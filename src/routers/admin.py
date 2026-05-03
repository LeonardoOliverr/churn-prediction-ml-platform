"""
Endpoints de administração da plataforma.

Requerem JWT Bearer token (Authorization: Bearer <token>).

POST /admin/tenants              — cria tenant
POST /admin/projects             — cria projeto
POST /admin/keys                 — gera API key (secret retornado uma única vez)
DELETE /admin/keys/{key_id}      — revoga API key
GET  /admin/tenants/{tenant_id}/keys — lista keys do tenant
"""

import secrets

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config import Settings, get_settings
from src.dependencies import get_current_admin, get_db
from src.middleware.auth import AdminClaims
from src.schemas.tenant import (
    ApiKeyCreate,
    ApiKeyRecord,
    ApiKeyResponse,
    ProjectCreate,
    ProjectResponse,
    TenantCreate,
    TenantResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])

_KEY_PREFIX_LENGTH = 20
_KEY_SECRET_LENGTH = 32


def _generate_api_key() -> tuple[str, str]:
    """Gera par (key_completa, prefixo). O prefixo é usado para lookup no banco."""
    secret_part = secrets.token_urlsafe(_KEY_SECRET_LENGTH)
    full_key = f"churn_live_sk_{secret_part}"
    prefix = full_key[:_KEY_PREFIX_LENGTH]
    return full_key, prefix


_ADMIN_RESPONSES = {
    401: {
        "description": "JWT ausente, expirado ou com assinatura inválida.",
        "content": {"application/json": {"example": {"error": "unauthorized", "message": "Token inválido ou expirado."}}},
    },
}


@router.post(
    "/tenants",
    response_model=TenantResponse,
    summary="Criar tenant",
    description="Cria um novo tenant na plataforma. O `slug` deve ser único e em `lowercase-kebab-case` — "
    "é o identificador usado em integrações externas e não pode ser alterado após a criação. "
    "Operação idempotente via `ON CONFLICT DO NOTHING` — retorna `409` se o slug já existir.",
    responses={
        **_ADMIN_RESPONSES,
        409: {
            "description": "Slug já existe.",
            "content": {"application/json": {"example": {"error": "conflict", "message": "Slug 'ibm-telco' já existe."}}},
        },
    },
)
def create_tenant(
    payload: TenantCreate,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> TenantResponse:
    """Cria um novo tenant. Requer JWT de admin."""
    row = db.execute(
        text("""
            INSERT INTO churn.tenants (name, slug)
            VALUES (:name, :slug)
            ON CONFLICT (slug) DO NOTHING
            RETURNING id, name, slug
        """),
        {"name": payload.name, "slug": payload.slug},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": f"Slug '{payload.slug}' já existe."})

    db.commit()
    logger.info("tenant_created", slug=payload.slug, by=admin.sub)
    return TenantResponse(id=str(row["id"]), name=row["name"], slug=row["slug"])


@router.post(
    "/projects",
    response_model=ProjectResponse,
    summary="Criar projeto",
    description="Cria um novo projeto dentro de um tenant. O `slug` deve ser único **por tenant** — "
    "dois projetos de tenants diferentes podem ter o mesmo slug. "
    "Um projeto é a unidade de isolamento de dados mais granular: cada projeto tem seu próprio modelo ativo "
    "configurado em `project_model_config` e seu próprio histórico de predições.",
    responses={
        **_ADMIN_RESPONSES,
        409: {
            "description": "Slug já existe neste tenant.",
            "content": {
                "application/json": {
                    "example": {"error": "conflict", "message": "Slug 'telco-churn-2018' já existe neste tenant."}
                }
            },
        },
    },
)
def create_project(
    payload: ProjectCreate,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectResponse:
    """Cria um novo projeto dentro de um tenant. Requer JWT de admin."""
    row = db.execute(
        text("""
            INSERT INTO churn.projects (tenant_id, name, slug)
            VALUES (:tenant_id, :name, :slug)
            ON CONFLICT (tenant_id, slug) DO NOTHING
            RETURNING id, tenant_id, name, slug
        """),
        {"tenant_id": payload.tenant_id, "name": payload.name, "slug": payload.slug},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": f"Slug '{payload.slug}' já existe neste tenant."})

    db.commit()
    logger.info("project_created", slug=payload.slug, tenant_id=payload.tenant_id, by=admin.sub)
    return ProjectResponse(id=str(row["id"]), tenant_id=str(row["tenant_id"]), name=row["name"], slug=row["slug"])


@router.post(
    "/keys",
    response_model=ApiKeyResponse,
    summary="Gerar API key",
    description="""
Gera uma nova API key para autenticação nos endpoints de inferência e histórico.

> **O campo `secret` é retornado apenas nesta resposta.** Armazene-o em um cofre de segredos
> (ex.: AWS Secrets Manager, HashiCorp Vault). Não é possível recuperá-lo posteriormente.

**Escopo de dados determinado pela key:**
- Com `project_id`: a key acessa dados e o modelo do projeto específico (nível 1 da cascade)
- Sem `project_id`: a key tem escopo de tenant (nível 2 da cascade — config ativa do tenant)
""",
    response_description="Dados da key gerada, incluindo o `secret` completo (retornado apenas uma vez).",
    responses=_ADMIN_RESPONSES,
)
def create_api_key(
    payload: ApiKeyCreate,
    db: Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
    admin: AdminClaims = Depends(get_current_admin),
) -> ApiKeyResponse:
    """Gera uma nova API key. O secret é retornado apenas nesta resposta."""
    full_key, prefix = _generate_api_key()
    key_hash = bcrypt.hashpw(full_key.encode(), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode()

    row = db.execute(
        text("""
            INSERT INTO churn.api_keys (tenant_id, project_id, key_prefix, key_hash, scopes, description, expires_at)
            VALUES (:tenant_id, :project_id, :key_prefix, :key_hash, :scopes, :description, :expires_at)
            RETURNING id, tenant_id, project_id, key_prefix, scopes, expires_at
        """),
        {
            "tenant_id":   payload.tenant_id,
            "project_id":  payload.project_id,
            "key_prefix":  prefix,
            "key_hash":    key_hash,
            "scopes":      payload.scopes,
            "description": payload.description,
            "expires_at":  payload.expires_at,
        },
    ).mappings().first()

    db.commit()
    logger.info("api_key_created", prefix=prefix, tenant_id=payload.tenant_id, by=admin.sub)

    return ApiKeyResponse(
        id=str(row["id"]),
        key_prefix=row["key_prefix"],
        secret=full_key,
        tenant_id=str(row["tenant_id"]),
        project_id=str(row["project_id"]) if row["project_id"] else None,
        scopes=list(row["scopes"]),
        expires_at=row["expires_at"],
    )


@router.delete(
    "/keys/{key_id}",
    summary="Revogar API key",
    description="Revoga uma API key pelo seu UUID. A key é marcada como `is_active = false` — "
    "operação **irreversível** por este endpoint. Requisições feitas com uma key revogada retornam `401`. "
    "O histórico de predições associado à key **não é afetado**.",
    responses={
        **_ADMIN_RESPONSES,
        404: {
            "description": "API key não encontrada.",
            "content": {"application/json": {"example": {"error": "not_found", "message": "API key não encontrada."}}},
        },
    },
)
def revoke_api_key(
    key_id: str,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
):
    """Desativa uma API key pelo ID. Requer JWT de admin."""
    result = db.execute(
        text("UPDATE churn.api_keys SET is_active = FALSE WHERE id = :id RETURNING id"),
        {"id": key_id},
    ).mappings().first()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "API key não encontrada."})

    db.commit()
    logger.info("api_key_revoked", key_id=key_id, by=admin.sub)
    return {"revoked": key_id}


@router.get(
    "/tenants/{tenant_id}/keys",
    response_model=list[ApiKeyRecord],
    summary="Listar API keys do tenant",
    description="Lista todas as API keys associadas ao tenant, incluindo keys revogadas (`is_active = false`). "
    "O campo `secret` **nunca é retornado** em listagens. "
    "Ordenação: keys mais recentes primeiro.",
    response_description="Lista de API keys do tenant (sem o `secret`).",
    responses=_ADMIN_RESPONSES,
)
def list_api_keys(
    tenant_id: str,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> list[ApiKeyRecord]:
    """Lista todas as API keys de um tenant. Requer JWT de admin."""
    rows = db.execute(
        text("""
            SELECT id, key_prefix, tenant_id, project_id, scopes, is_active, created_at, expires_at, last_used_at
            FROM churn.api_keys
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
        """),
        {"tenant_id": tenant_id},
    ).mappings().all()

    return [
        ApiKeyRecord(
            id=str(r["id"]),
            key_prefix=r["key_prefix"],
            tenant_id=str(r["tenant_id"]),
            project_id=str(r["project_id"]) if r["project_id"] else None,
            scopes=list(r["scopes"]),
            is_active=r["is_active"],
            created_at=str(r["created_at"]),
            expires_at=str(r["expires_at"]) if r["expires_at"] else None,
            last_used_at=str(r["last_used_at"]) if r["last_used_at"] else None,
        )
        for r in rows
    ]
