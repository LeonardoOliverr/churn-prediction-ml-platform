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
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config import Settings, get_settings
from src.dependencies import get_current_admin, get_db
from src.middleware.auth import AdminClaims
from src.schemas.tenant import (
    ApiKeyCreate,
    ApiKeyRecord,
    ApiKeyResponse,
    ChampionModelConfigure,
    ChallengerModelConfigure,
    ModelDeactivationRequest,
    ModelPromotionRequest,
    ProjectModelConfigListResponse,
    ProjectModelConfigRecord,
    ProjectModelConfigResponse,
    ProjectCreate,
    ProjectResponse,
    TenantCreate,
    TenantResponse,
)
from src.services.model_resolver import invalidate_model_cache

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


def _not_found(message: str) -> HTTPException:
    """Cria erro 404 padronizado."""
    return HTTPException(status_code=404, detail={"error": "not_found", "message": message})


def _conflict(message: str) -> HTTPException:
    """Cria erro 409 padronizado."""
    return HTTPException(status_code=409, detail={"error": "conflict", "message": message})


def _get_project(db: Connection, project_id: str) -> dict:
    """Busca projeto e tenant para validar escopo de configuração."""
    row = db.execute(
        text("""
            SELECT p.id, p.tenant_id, p.name, p.slug
            FROM churn.projects p
            WHERE p.id = :project_id
        """),
        {"project_id": project_id},
    ).mappings().first()
    if not row:
        raise _not_found("Projeto não encontrado.")
    return dict(row)


def _get_tenant(db: Connection, tenant_id: str) -> dict:
    """Busca tenant para validar escopo de configuração."""
    row = db.execute(
        text("""
            SELECT id, name, slug
            FROM churn.tenants
            WHERE id = :tenant_id
        """),
        {"tenant_id": tenant_id},
    ).mappings().first()
    if not row:
        raise _not_found("Tenant não encontrado.")
    return dict(row)


def _get_model(db: Connection, model_id: str) -> dict:
    """Busca modelo no catálogo técnico."""
    row = db.execute(
        text("""
            SELECT id, tenant_id, project_id, name, version, scope, status
            FROM churn.models
            WHERE id = :model_id
        """),
        {"model_id": model_id},
    ).mappings().first()
    if not row:
        raise _not_found("Modelo não encontrado.")
    return dict(row)


def _validate_model_for_scope(
    db: Connection,
    tenant_id: str,
    project_id: str | None,
    model_id: str,
) -> dict:
    """Valida elegibilidade técnica e compatibilidade multi-tenant do modelo."""
    model = _get_model(db, model_id)

    if model["status"] != "approved":
        raise _conflict("Modelo precisa estar com status='approved' para uso em produção.")

    scope = model["scope"]
    if scope == "global":
        return model
    if scope == "tenant" and str(model["tenant_id"]) == str(tenant_id):
        return model
    if project_id is not None and scope == "project" and str(model["project_id"]) == str(project_id):
        return model

    raise _conflict("Modelo não é compatível com o tenant/projeto informado.")


def _validate_model_for_project(db: Connection, project: dict, model_id: str) -> dict:
    """Valida elegibilidade técnica e compatibilidade do modelo com um projeto."""
    return _validate_model_for_scope(db, str(project["tenant_id"]), str(project["id"]), model_id)


def _record_from_row(row) -> ProjectModelConfigRecord:
    """Converte linha SQL em schema de resposta."""
    return ProjectModelConfigRecord(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        project_id=str(row["project_id"]) if row["project_id"] else None,
        model_id=str(row["model_id"]),
        model_name=row["model_name"],
        model_version=str(row["model_version"]),
        model_status=row["model_status"],
        role=row["role"],
        threshold=float(row["threshold"]),
        traffic_split=float(row["traffic_split"]),
        is_active=bool(row["is_active"]),
        environment=row["environment"],
        configured_by=row["configured_by"],
        description=row["description"],
        activation_reason=row["activation_reason"],
        configured_at=str(row["configured_at"]),
        deactivated_at=str(row["deactivated_at"]) if row["deactivated_at"] else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _select_config(db: Connection, config_id: str) -> ProjectModelConfigRecord:
    """Busca uma configuração pelo ID para resposta da API."""
    row = db.execute(
        text("""
            SELECT
                pmc.id, pmc.tenant_id, pmc.project_id, pmc.model_id,
                pmc.threshold, pmc.is_active, pmc.configured_at,
                pmc.configured_by, pmc.description, pmc.deactivated_at,
                pmc.activation_reason, pmc.environment, pmc.created_at,
                pmc.updated_at, pmc.role, pmc.traffic_split,
                m.name AS model_name, m.version AS model_version, m.status AS model_status
            FROM churn.project_model_config pmc
            JOIN churn.models m ON m.id = pmc.model_id
            WHERE pmc.id = :config_id
        """),
        {"config_id": config_id},
    ).mappings().first()
    if not row:
        raise _not_found("Configuração de modelo não encontrada.")
    return _record_from_row(row)


def _active_config_by_role(db: Connection, tenant_id: str, project_id: str | None, role: str):
    """Busca configuração ativa por papel operacional."""
    return db.execute(
        text("""
            SELECT id, model_id, role
            FROM churn.project_model_config
            WHERE tenant_id = :tenant_id
              AND project_id IS NOT DISTINCT FROM :project_id
              AND environment = 'production'
              AND is_active = TRUE
              AND role = :role
            ORDER BY configured_at DESC, id DESC
            LIMIT 1
        """),
        {"tenant_id": tenant_id, "project_id": project_id, "role": role},
    ).mappings().first()


def _active_config_by_model(db: Connection, tenant_id: str, project_id: str | None, model_id: str):
    """Busca configuração ativa de um modelo no projeto."""
    return db.execute(
        text("""
            SELECT id, model_id, role
            FROM churn.project_model_config
            WHERE tenant_id = :tenant_id
              AND project_id IS NOT DISTINCT FROM :project_id
              AND model_id = :model_id
              AND environment = 'production'
              AND is_active = TRUE
            ORDER BY configured_at DESC, id DESC
            LIMIT 1
        """),
        {"tenant_id": tenant_id, "project_id": project_id, "model_id": model_id},
    ).mappings().first()


def _deactivate_role(db: Connection, tenant_id: str, project_id: str | None, role: str) -> None:
    """Desativa configurações ativas por papel operacional."""
    db.execute(
        text("""
            UPDATE churn.project_model_config
            SET
                is_active = FALSE,
                deactivated_at = COALESCE(deactivated_at, NOW()),
                updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND project_id IS NOT DISTINCT FROM :project_id
              AND environment = 'production'
              AND role = :role
              AND is_active = TRUE
        """),
        {"tenant_id": tenant_id, "project_id": project_id, "role": role},
    )


def _deactivate_model_config(
    db: Connection,
    tenant_id: str,
    project_id: str | None,
    model_id: str,
    reason: str,
) -> None:
    """Desativa configuração ativa de um modelo específico."""
    db.execute(
        text("""
            UPDATE churn.project_model_config
            SET
                is_active = FALSE,
                deactivated_at = COALESCE(deactivated_at, NOW()),
                activation_reason = :reason,
                updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND project_id IS NOT DISTINCT FROM :project_id
              AND model_id = :model_id
              AND environment = 'production'
              AND is_active = TRUE
        """),
        {"tenant_id": tenant_id, "project_id": project_id, "model_id": model_id, "reason": reason},
    )


def _upsert_model_config(
    db: Connection,
    tenant_id: str,
    project_id: str | None,
    model_id: str,
    role: str,
    threshold: float,
    traffic_split: float,
    configured_by: str,
    activation_reason: str | None,
    description: str | None,
) -> ProjectModelConfigRecord:
    """Cria ou reativa a configuração operacional de um modelo."""
    row = db.execute(
        text("""
            INSERT INTO churn.project_model_config
                (tenant_id, project_id, model_id, threshold, is_active,
                 configured_at, configured_by, description, activation_reason,
                 environment, role, traffic_split, deactivated_at, created_at, updated_at)
            VALUES
                (:tenant_id, :project_id, :model_id, :threshold, TRUE,
                 NOW(), :configured_by, :description, :activation_reason,
                 'production', :role, :traffic_split, NULL, NOW(), NOW())
            ON CONFLICT (tenant_id, project_id, model_id, environment)
            DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                project_id = EXCLUDED.project_id,
                threshold = EXCLUDED.threshold,
                is_active = TRUE,
                configured_at = NOW(),
                configured_by = EXCLUDED.configured_by,
                description = EXCLUDED.description,
                activation_reason = EXCLUDED.activation_reason,
                environment = 'production',
                role = EXCLUDED.role,
                traffic_split = EXCLUDED.traffic_split,
                deactivated_at = NULL,
                updated_at = NOW()
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "model_id": model_id,
            "threshold": threshold,
            "configured_by": configured_by,
            "description": description,
            "activation_reason": activation_reason,
            "role": role,
            "traffic_split": traffic_split,
        },
    ).mappings().first()
    return _select_config(db, str(row["id"]))


def _list_model_config(
    db: Connection,
    tenant_id: str,
    project_id: str | None,
) -> ProjectModelConfigListResponse:
    """Lista champion, challenger e histórico recente de um escopo."""
    rows = db.execute(
        text("""
            SELECT
                pmc.id, pmc.tenant_id, pmc.project_id, pmc.model_id,
                pmc.threshold, pmc.is_active, pmc.configured_at,
                pmc.configured_by, pmc.description, pmc.deactivated_at,
                pmc.activation_reason, pmc.environment, pmc.created_at,
                pmc.updated_at, pmc.role, pmc.traffic_split,
                m.name AS model_name, m.version AS model_version, m.status AS model_status
            FROM churn.project_model_config pmc
            JOIN churn.models m ON m.id = pmc.model_id
            WHERE pmc.tenant_id = :tenant_id
              AND pmc.project_id IS NOT DISTINCT FROM :project_id
              AND pmc.environment = 'production'
            ORDER BY pmc.is_active DESC, pmc.configured_at DESC, pmc.id DESC
            LIMIT 20
        """),
        {"tenant_id": tenant_id, "project_id": project_id},
    ).mappings().all()

    records = [_record_from_row(row) for row in rows]
    champion = next((record for record in records if record.is_active and record.role == "champion"), None)
    challenger = next((record for record in records if record.is_active and record.role == "challenger"), None)
    return ProjectModelConfigListResponse(champion=champion, challenger=challenger, history=records)


def _configure_champion_for_scope(
    db: Connection,
    admin: AdminClaims,
    tenant_id: str,
    project_id: str | None,
    payload: ChampionModelConfigure,
) -> ProjectModelConfigResponse:
    """Ativa um modelo aprovado como champion em tenant ou projeto."""
    _validate_model_for_scope(db, tenant_id, project_id, payload.model_id)
    _deactivate_role(db, tenant_id, project_id, "champion")
    config = _upsert_model_config(
        db=db,
        tenant_id=tenant_id,
        project_id=project_id,
        model_id=payload.model_id,
        role="champion",
        threshold=payload.threshold,
        traffic_split=0.0,
        configured_by=admin.sub,
        activation_reason=payload.activation_reason,
        description=payload.description,
    )
    db.commit()
    invalidate_model_cache(tenant_id, project_id)
    return ProjectModelConfigResponse(config=config)


def _configure_challenger_for_scope(
    db: Connection,
    admin: AdminClaims,
    tenant_id: str,
    project_id: str | None,
    payload: ChallengerModelConfigure,
) -> ProjectModelConfigResponse:
    """Ativa um modelo aprovado como challenger em tenant ou projeto."""
    _validate_model_for_scope(db, tenant_id, project_id, payload.model_id)

    active = _active_config_by_model(db, tenant_id, project_id, payload.model_id)
    if active and active["role"] == "champion":
        raise _conflict("O champion ativo nÃ£o pode ser configurado simultaneamente como challenger.")

    _deactivate_role(db, tenant_id, project_id, "challenger")
    config = _upsert_model_config(
        db=db,
        tenant_id=tenant_id,
        project_id=project_id,
        model_id=payload.model_id,
        role="challenger",
        threshold=payload.threshold,
        traffic_split=payload.traffic_split,
        configured_by=admin.sub,
        activation_reason=payload.activation_reason,
        description=payload.description,
    )
    db.commit()
    invalidate_model_cache(tenant_id, project_id)
    return ProjectModelConfigResponse(config=config)


def _promote_challenger_for_scope(
    db: Connection,
    admin: AdminClaims,
    tenant_id: str,
    project_id: str | None,
    model_id: str,
    payload: ModelPromotionRequest,
) -> ProjectModelConfigResponse:
    """Promove challenger ativo para champion em tenant ou projeto."""
    challenger = _active_config_by_model(db, tenant_id, project_id, model_id)
    if not challenger or challenger["role"] != "challenger":
        raise _conflict("O modelo informado nÃ£o Ã© o challenger ativo deste escopo.")

    _deactivate_role(db, tenant_id, project_id, "champion")
    row = db.execute(
        text("""
            UPDATE churn.project_model_config
            SET
                role = 'champion',
                traffic_split = 0.000,
                activation_reason = COALESCE(:reason, activation_reason),
                configured_by = :configured_by,
                configured_at = NOW(),
                updated_at = NOW()
            WHERE id = :config_id
            RETURNING id
        """),
        {"config_id": str(challenger["id"]), "reason": payload.activation_reason, "configured_by": admin.sub},
    ).mappings().first()

    config = _select_config(db, str(row["id"]))
    db.commit()
    invalidate_model_cache(tenant_id, project_id)
    return ProjectModelConfigResponse(config=config)


def _deactivate_model_for_scope(
    db: Connection,
    admin: AdminClaims,
    tenant_id: str,
    project_id: str | None,
    model_id: str,
    payload: ModelDeactivationRequest,
) -> ProjectModelConfigResponse:
    """Desativa challenger ou substitui champion em tenant ou projeto."""
    active = _active_config_by_model(db, tenant_id, project_id, model_id)
    if not active:
        raise _not_found("ConfiguraÃ§Ã£o ativa do modelo nÃ£o encontrada neste escopo.")

    if active["role"] == "challenger":
        _deactivate_model_config(db, tenant_id, project_id, model_id, payload.reason)
        config = _select_config(db, str(active["id"]))
        db.commit()
        invalidate_model_cache(tenant_id, project_id)
        return ProjectModelConfigResponse(config=config)

    if payload.replacement_model_id is None:
        raise _conflict("Champion nÃ£o pode ser desligado sem replacement_model_id.")

    if payload.replacement_model_id == model_id:
        raise _conflict("replacement_model_id deve ser diferente do champion atual.")

    replacement_model = _validate_model_for_scope(db, tenant_id, project_id, payload.replacement_model_id)
    current_config = _select_config(db, str(active["id"]))
    _deactivate_model_config(db, tenant_id, project_id, model_id, payload.reason)
    replacement = _upsert_model_config(
        db=db,
        tenant_id=tenant_id,
        project_id=project_id,
        model_id=str(replacement_model["id"]),
        role="champion",
        threshold=current_config.threshold,
        traffic_split=0.0,
        configured_by=admin.sub,
        activation_reason=payload.reason,
        description=f"Replacement for {model_id}",
    )
    db.commit()
    invalidate_model_cache(tenant_id, project_id)
    return ProjectModelConfigResponse(config=replacement)


def _resolve_admin_model_scope(db: Connection, tenant_id: str, project_id: str | None) -> tuple[str, str | None]:
    """Valida tenant e, se informado, projeto pertencente ao tenant."""
    _get_tenant(db, tenant_id)
    if project_id is None:
        return tenant_id, None

    project = _get_project(db, project_id)
    if str(project["tenant_id"]) != str(tenant_id):
        raise _conflict("Projeto nÃ£o pertence ao tenant informado.")
    return tenant_id, project_id


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


@router.get(
    "/tenants/{tenant_id}/models/config",
    response_model=ProjectModelConfigListResponse,
    summary="Listar configurações de modelos do tenant",
    responses=_ADMIN_RESPONSES,
)
def list_tenant_model_config(
    tenant_id: str,
    project_id: str | None = Query(
        default=None,
        description="Opcional. Quando informado, lista a configuracao tenant + project; omitido lista a configuracao do tenant.",
    ),
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigListResponse:
    """Lista champion, challenger e historico recente do tenant ou projeto."""
    tenant_id, project_id = _resolve_admin_model_scope(db, tenant_id, project_id)
    logger.info("tenant_model_config_listed", tenant_id=tenant_id, project_id=project_id, by=admin.sub)
    return _list_model_config(db, tenant_id, project_id)


@router.post(
    "/tenants/{tenant_id}/models/champion",
    response_model=ProjectModelConfigResponse,
    summary="Configurar champion do tenant",
    responses=_ADMIN_RESPONSES,
)
def configure_tenant_champion(
    tenant_id: str,
    payload: ChampionModelConfigure,
    project_id: str | None = Query(
        default=None,
        description="Opcional. Quando informado, configura champion para tenant + project; omitido configura champion do tenant.",
    ),
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Ativa um modelo aprovado como champion do tenant ou projeto."""
    tenant_id, project_id = _resolve_admin_model_scope(db, tenant_id, project_id)
    logger.info("tenant_champion_configured", tenant_id=tenant_id, project_id=project_id, model_id=payload.model_id, by=admin.sub)
    return _configure_champion_for_scope(db, admin, tenant_id, project_id, payload)


@router.post(
    "/tenants/{tenant_id}/models/challenger",
    response_model=ProjectModelConfigResponse,
    summary="Configurar challenger do tenant",
    responses=_ADMIN_RESPONSES,
)
def configure_tenant_challenger(
    tenant_id: str,
    payload: ChallengerModelConfigure,
    project_id: str | None = Query(
        default=None,
        description="Opcional. Quando informado, configura challenger para tenant + project; omitido configura challenger do tenant.",
    ),
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Ativa um modelo aprovado como challenger do tenant ou projeto."""
    tenant_id, project_id = _resolve_admin_model_scope(db, tenant_id, project_id)
    logger.info(
        "tenant_challenger_configured",
        tenant_id=tenant_id,
        project_id=project_id,
        model_id=payload.model_id,
        traffic_split=payload.traffic_split,
        by=admin.sub,
    )
    return _configure_challenger_for_scope(db, admin, tenant_id, project_id, payload)


@router.post(
    "/tenants/{tenant_id}/models/{model_id}/promote",
    response_model=ProjectModelConfigResponse,
    summary="Promover challenger do tenant a champion",
    responses=_ADMIN_RESPONSES,
)
def promote_tenant_challenger(
    tenant_id: str,
    model_id: str,
    payload: ModelPromotionRequest,
    project_id: str | None = Query(
        default=None,
        description="Opcional. Quando informado, promove challenger de tenant + project; omitido promove challenger do tenant.",
    ),
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Promove o challenger ativo do tenant ou projeto para champion."""
    tenant_id, project_id = _resolve_admin_model_scope(db, tenant_id, project_id)
    logger.info("tenant_challenger_promoted", tenant_id=tenant_id, project_id=project_id, model_id=model_id, by=admin.sub)
    return _promote_challenger_for_scope(db, admin, tenant_id, project_id, model_id, payload)


@router.post(
    "/tenants/{tenant_id}/models/{model_id}/deactivate",
    response_model=ProjectModelConfigResponse,
    summary="Desligar modelo da produção do tenant",
    responses=_ADMIN_RESPONSES,
)
def deactivate_tenant_model_config(
    tenant_id: str,
    model_id: str,
    payload: ModelDeactivationRequest,
    project_id: str | None = Query(
        default=None,
        description="Opcional. Quando informado, desliga modelo de tenant + project; omitido desliga modelo do tenant.",
    ),
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Desativa challenger ou substitui champion do tenant ou projeto."""
    tenant_id, project_id = _resolve_admin_model_scope(db, tenant_id, project_id)
    logger.info("tenant_model_config_deactivated", tenant_id=tenant_id, project_id=project_id, model_id=model_id, by=admin.sub)
    return _deactivate_model_for_scope(db, admin, tenant_id, project_id, model_id, payload)


@router.get(
    "/projects/{project_id}/models/config",
    response_model=ProjectModelConfigListResponse,
    include_in_schema=False,
    summary="Listar configurações de modelos do projeto",
    responses=_ADMIN_RESPONSES,
)
def list_project_model_config(
    project_id: str,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigListResponse:
    """Lista champion, challenger e histórico recente de configurações."""
    project = _get_project(db, project_id)
    logger.info("project_model_config_listed", project_id=project_id, by=admin.sub)
    return _list_model_config(db, str(project["tenant_id"]), project_id)
    rows = db.execute(
        text("""
            SELECT
                pmc.id, pmc.tenant_id, pmc.project_id, pmc.model_id,
                pmc.threshold, pmc.is_active, pmc.configured_at,
                pmc.configured_by, pmc.description, pmc.deactivated_at,
                pmc.activation_reason, pmc.environment, pmc.created_at,
                pmc.updated_at, pmc.role, pmc.traffic_split,
                m.name AS model_name, m.version AS model_version, m.status AS model_status
            FROM churn.project_model_config pmc
            JOIN churn.models m ON m.id = pmc.model_id
            WHERE pmc.project_id = :project_id
              AND pmc.environment = 'production'
            ORDER BY pmc.is_active DESC, pmc.configured_at DESC, pmc.id DESC
            LIMIT 20
        """),
        {"project_id": project_id},
    ).mappings().all()

    records = [_record_from_row(row) for row in rows]
    champion = next((record for record in records if record.is_active and record.role == "champion"), None)
    challenger = next((record for record in records if record.is_active and record.role == "challenger"), None)
    logger.info("project_model_config_listed", project_id=project_id, by=admin.sub)
    return ProjectModelConfigListResponse(champion=champion, challenger=challenger, history=records)


@router.post(
    "/projects/{project_id}/models/champion",
    response_model=ProjectModelConfigResponse,
    include_in_schema=False,
    summary="Configurar champion do projeto",
    responses=_ADMIN_RESPONSES,
)
def configure_champion(
    project_id: str,
    payload: ChampionModelConfigure,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Ativa um modelo aprovado como champion do projeto."""
    project = _get_project(db, project_id)
    logger.info("champion_configured", project_id=project_id, model_id=payload.model_id, by=admin.sub)
    return _configure_champion_for_scope(db, admin, str(project["tenant_id"]), project_id, payload)

    _validate_model_for_project(db, project, payload.model_id)

    _deactivate_role(db, project_id, "champion")
    config = _upsert_model_config(
        db=db,
        project=project,
        model_id=payload.model_id,
        role="champion",
        threshold=payload.threshold,
        traffic_split=0.0,
        configured_by=admin.sub,
        activation_reason=payload.activation_reason,
        description=payload.description,
    )
    db.commit()
    invalidate_model_cache(str(project["tenant_id"]), project_id)
    logger.info("champion_configured", project_id=project_id, model_id=payload.model_id, by=admin.sub)
    return ProjectModelConfigResponse(config=config)


@router.post(
    "/projects/{project_id}/models/challenger",
    response_model=ProjectModelConfigResponse,
    include_in_schema=False,
    summary="Configurar challenger do projeto",
    responses=_ADMIN_RESPONSES,
)
def configure_challenger(
    project_id: str,
    payload: ChallengerModelConfigure,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Ativa um modelo aprovado como challenger do projeto."""
    project = _get_project(db, project_id)
    logger.info(
        "challenger_configured",
        project_id=project_id,
        model_id=payload.model_id,
        traffic_split=payload.traffic_split,
        by=admin.sub,
    )
    return _configure_challenger_for_scope(db, admin, str(project["tenant_id"]), project_id, payload)

    _validate_model_for_project(db, project, payload.model_id)

    active = _active_config_by_model(db, project_id, payload.model_id)
    if active and active["role"] == "champion":
        raise _conflict("O champion ativo não pode ser configurado simultaneamente como challenger.")

    _deactivate_role(db, project_id, "challenger")
    config = _upsert_model_config(
        db=db,
        project=project,
        model_id=payload.model_id,
        role="challenger",
        threshold=payload.threshold,
        traffic_split=payload.traffic_split,
        configured_by=admin.sub,
        activation_reason=payload.activation_reason,
        description=payload.description,
    )
    db.commit()
    invalidate_model_cache(str(project["tenant_id"]), project_id)
    logger.info(
        "challenger_configured",
        project_id=project_id,
        model_id=payload.model_id,
        traffic_split=payload.traffic_split,
        by=admin.sub,
    )
    return ProjectModelConfigResponse(config=config)


@router.post(
    "/projects/{project_id}/models/{model_id}/promote",
    response_model=ProjectModelConfigResponse,
    include_in_schema=False,
    summary="Promover challenger a champion",
    responses=_ADMIN_RESPONSES,
)
def promote_challenger(
    project_id: str,
    model_id: str,
    payload: ModelPromotionRequest,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Promove o challenger ativo para champion."""
    project = _get_project(db, project_id)
    logger.info("challenger_promoted", project_id=project_id, model_id=model_id, by=admin.sub)
    return _promote_challenger_for_scope(db, admin, str(project["tenant_id"]), project_id, model_id, payload)

    challenger = _active_config_by_model(db, project_id, model_id)
    if not challenger or challenger["role"] != "challenger":
        raise _conflict("O modelo informado não é o challenger ativo do projeto.")

    _deactivate_role(db, project_id, "champion")
    row = db.execute(
        text("""
            UPDATE churn.project_model_config
            SET
                role = 'champion',
                traffic_split = 0.000,
                activation_reason = COALESCE(:reason, activation_reason),
                configured_by = :configured_by,
                configured_at = NOW(),
                updated_at = NOW()
            WHERE id = :config_id
            RETURNING id
        """),
        {"config_id": str(challenger["id"]), "reason": payload.activation_reason, "configured_by": admin.sub},
    ).mappings().first()

    config = _select_config(db, str(row["id"]))
    db.commit()
    invalidate_model_cache(str(project["tenant_id"]), project_id)
    logger.info("challenger_promoted", project_id=project_id, model_id=model_id, by=admin.sub)
    return ProjectModelConfigResponse(config=config)


@router.post(
    "/projects/{project_id}/models/{model_id}/deactivate",
    response_model=ProjectModelConfigResponse,
    include_in_schema=False,
    summary="Desligar modelo da produção",
    responses=_ADMIN_RESPONSES,
)
def deactivate_model_config(
    project_id: str,
    model_id: str,
    payload: ModelDeactivationRequest,
    db: Connection = Depends(get_db),
    admin: AdminClaims = Depends(get_current_admin),
) -> ProjectModelConfigResponse:
    """Desativa challenger ou substitui champion por outro modelo aprovado."""
    project = _get_project(db, project_id)
    logger.info("model_config_deactivated", project_id=project_id, model_id=model_id, by=admin.sub)
    return _deactivate_model_for_scope(db, admin, str(project["tenant_id"]), project_id, model_id, payload)

    active = _active_config_by_model(db, project_id, model_id)
    if not active:
        raise _not_found("Configuração ativa do modelo não encontrada neste projeto.")

    if active["role"] == "challenger":
        _deactivate_model_config(db, project_id, model_id, payload.reason)
        config = _select_config(db, str(active["id"]))
        db.commit()
        invalidate_model_cache(str(project["tenant_id"]), project_id)
        logger.info("challenger_deactivated", project_id=project_id, model_id=model_id, by=admin.sub)
        return ProjectModelConfigResponse(config=config)

    if payload.replacement_model_id is None:
        raise _conflict("Champion não pode ser desligado sem replacement_model_id.")

    if payload.replacement_model_id == model_id:
        raise _conflict("replacement_model_id deve ser diferente do champion atual.")

    replacement_model = _validate_model_for_project(db, project, payload.replacement_model_id)
    current_config = _select_config(db, str(active["id"]))
    _deactivate_model_config(db, project_id, model_id, payload.reason)
    replacement = _upsert_model_config(
        db=db,
        project=project,
        model_id=str(replacement_model["id"]),
        role="champion",
        threshold=current_config.threshold,
        traffic_split=0.0,
        configured_by=admin.sub,
        activation_reason=payload.reason,
        description=f"Replacement for {model_id}",
    )
    db.commit()
    invalidate_model_cache(str(project["tenant_id"]), project_id)
    logger.info(
        "champion_replaced",
        project_id=project_id,
        old_model_id=model_id,
        replacement_model_id=payload.replacement_model_id,
        by=admin.sub,
    )
    return ProjectModelConfigResponse(config=replacement)
