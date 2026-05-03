"""
Dependências FastAPI reutilizadas pelos routers.

Inclui:
  - Engine SQLAlchemy singleton com pool
  - Gerador de conexão por request (get_db)
  - Autenticação por API key com cache TTL (get_current_api_key)
  - Autenticação JWT para endpoints admin (get_current_admin)
  - Factory de verificação de escopos (require_scope)
"""

from datetime import datetime, timezone
from typing import Generator, Optional

import bcrypt
import structlog
from cachetools import TTLCache
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from src.config import Settings, get_settings
from src.middleware.auth import AdminClaims, ApiKeyRecord

logger = structlog.get_logger()

# Cache de API keys validadas: chave completa -> ApiKeyRecord
# Tamanho máximo 2048 entradas; TTL definido dinamicamente pela Settings
_api_key_cache: TTLCache = TTLCache(maxsize=2048, ttl=60)

_engine: Optional[Engine] = None


def _get_engine(settings: Optional[Settings] = None) -> Engine:
    """Retorna engine SQLAlchemy singleton. Cria com pool_pre_ping na primeira chamada."""
    global _engine
    if _engine is None:
        cfg = settings or get_settings()
        _engine = create_engine(cfg.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
    return _engine


# Scheme HTTPBearer — registra o botão "Authorize" no Swagger UI
_bearer_scheme = HTTPBearer(auto_error=False)


def get_db(settings: Settings = Depends(get_settings)) -> Generator[Connection, None, None]:
    """Gera uma conexão SQLAlchemy por request e a fecha ao final."""
    with _get_engine(settings).connect() as conn:
        yield conn


def _lookup_api_key(key: str, db: Connection) -> Optional[ApiKeyRecord]:
    """Busca, valida hash bcrypt e retorna ApiKeyRecord. Retorna None em qualquer falha."""
    prefix = key[:20]
    row = db.execute(
        text("""
            SELECT id, tenant_id, project_id, key_hash, scopes, is_active, expires_at, key_prefix
            FROM churn.api_keys
            WHERE key_prefix = :prefix
              AND is_active   = TRUE
        """),
        {"prefix": prefix},
    ).mappings().first()

    if not row:
        return None

    # Verificação bcrypt — intencional lentidão para proteção contra brute-force
    try:
        valid = bcrypt.checkpw(key.encode(), row["key_hash"].encode())
    except Exception:
        return None

    if not valid:
        return None

    # Verifica expiração
    if row["expires_at"] is not None:
        expires = row["expires_at"]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            return None

    return ApiKeyRecord(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        project_id=str(row["project_id"]) if row["project_id"] else None,
        scopes=list(row["scopes"]) if row["scopes"] else [],
        key_prefix=row["key_prefix"],
    )


def _update_last_used(key_id: str, engine: Engine) -> None:
    """Atualiza last_used_at da API key em background. Falhas são silenciosas."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE churn.api_keys SET last_used_at = NOW() WHERE id = :id"),
                {"id": key_id},
            )
    except Exception as exc:
        logger.warning("last_used_update_failed", key_id=key_id, error=str(exc))


def get_current_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
    db: Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiKeyRecord:
    """Valida API key do header x-api-key. Usa cache TTL para evitar bcrypt em toda request."""
    global _api_key_cache

    unauthorized = HTTPException(
        status_code=401,
        detail={"error": "invalid_api_key", "message": "API key inválida ou revogada.", "request_id": "unknown"},
    )

    if not x_api_key:
        raise unauthorized

    # Recria cache se o TTL configurado tiver mudado desde a última inicialização
    if _api_key_cache.ttl != settings.api_key_cache_ttl_seconds:
        _api_key_cache = TTLCache(maxsize=2048, ttl=settings.api_key_cache_ttl_seconds)

    # Verifica cache antes de ir ao banco (evita bcrypt a cada request)
    cached = _api_key_cache.get(x_api_key)
    if cached is not None:
        return cached

    record = _lookup_api_key(x_api_key, db)
    if record is None:
        raise unauthorized

    _api_key_cache[x_api_key] = record

    # Atualiza last_used_at sem bloquear a resposta
    _update_last_used(record.id, _get_engine(settings))

    logger.info("api_key_authenticated", key_prefix=record.key_prefix, tenant_id=record.tenant_id)
    return record


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AdminClaims:
    """Valida JWT Bearer via HTTPBearer scheme (compatível com Swagger UI)."""
    unauthorized = HTTPException(
        status_code=401,
        detail={"error": "invalid_token", "message": "Token JWT inválido ou expirado.", "request_id": "unknown"},
    )

    if not credentials:
        raise unauthorized

    try:
        payload = jwt.decode(credentials.credentials, settings.app_secret_key, algorithms=["HS256"])
    except JWTError:
        raise unauthorized

    sub = payload.get("sub")
    exp = payload.get("exp")
    if not sub or not exp:
        raise unauthorized

    return AdminClaims(sub=str(sub), exp=int(exp), extra={k: v for k, v in payload.items() if k not in ("sub", "exp")})


def require_scope(scope: str):
    """Factory que retorna uma dependência verificando se a API key possui o escopo necessário."""
    def _check(api_key: ApiKeyRecord = Depends(get_current_api_key)) -> ApiKeyRecord:
        if scope not in api_key.scopes:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "scope_insufficient",
                    "message": f"Escopo '{scope}' necessário.",
                    "request_id": "unknown",
                },
            )
        return api_key
    return _check
