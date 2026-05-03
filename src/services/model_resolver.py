"""
Resolução de modelo em produção por projeto com cache LRU+TTL.

Produção é definida exclusivamente por churn.project_model_config.is_active.
churn.models.status indica elegibilidade técnica; somente modelos approved
podem ser servidos.

Cascade de resolução:
  1º project_model_config do projeto  (API key com project_id)
  2º project_model_config do tenant   (API key sem project_id)
  3º churn.models scope=global        (modelo global aprovado)
"""

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

import mlflow.sklearn
import structlog
from fastapi import HTTPException
from sqlalchemy import text

logger = structlog.get_logger()

# Cache LRU+TTL: chave (tenant_id, project_id) -> (pipeline, threshold, record, loaded_at)
_cache: OrderedDict = OrderedDict()
_cache_lock = Lock()
_MAX_CACHE_SIZE = 128

_SQL_PROJECT_MODEL_CONFIG = text("""
    SELECT
        m.id,
        m.mlflow_run_id,
        m.version,
        m.name,
        COALESCE(pmc.threshold, 0.5) AS threshold
    FROM churn.project_model_config pmc
    JOIN churn.models m ON m.id = pmc.model_id
    WHERE pmc.tenant_id  = :tenant_id
      AND pmc.project_id = :project_id
      AND pmc.is_active  = TRUE
      AND m.status       = 'approved'
    ORDER BY pmc.configured_at DESC
    LIMIT 1
""")

_SQL_TENANT_MODEL_CONFIG = text("""
    SELECT
        m.id,
        m.mlflow_run_id,
        m.version,
        m.name,
        COALESCE(pmc.threshold, 0.5) AS threshold
    FROM churn.project_model_config pmc
    JOIN churn.models m ON m.id = pmc.model_id
    WHERE pmc.tenant_id = :tenant_id
      AND pmc.is_active = TRUE
      AND m.status      = 'approved'
    ORDER BY pmc.configured_at DESC
    LIMIT 1
""")

_SQL_GLOBAL_MODEL = text("""
    SELECT
        m.id,
        m.mlflow_run_id,
        m.version,
        m.name,
        0.5 AS threshold
    FROM churn.models m
    WHERE m.scope  = 'global'
      AND m.status = 'approved'
    ORDER BY m.created_at DESC
    LIMIT 1
""")


def _model_not_found(tenant_id: str, project_id: Optional[str]) -> HTTPException:
    """Cria erro padronizado quando não há modelo de produção configurado."""
    return HTTPException(
        status_code=404,
        detail={
            "error": "model_not_found",
            "message": (
                "Nenhum modelo aprovado em produção encontrado "
                f"para tenant_id={tenant_id} e project_id={project_id}"
            ),
            "request_id": "unknown",
        },
    )


def _query_active_model(tenant_id: str, project_id: Optional[str], db) -> dict:
    """Resolve modelo com cascade: projeto → tenant → global.

    Nível 1 — configuração explícita do projeto (project_id da API key).
    Nível 2 — configuração ativa mais recente do tenant (API key sem projeto).
    Nível 3 — modelo global aprovado mais recente (fallback universal).
    """
    if project_id is not None:
        row = db.execute(
            _SQL_PROJECT_MODEL_CONFIG,
            {"tenant_id": tenant_id, "project_id": project_id},
        ).mappings().first()
        if row:
            return dict(row)

    row = db.execute(
        _SQL_TENANT_MODEL_CONFIG,
        {"tenant_id": tenant_id},
    ).mappings().first()
    if row:
        return dict(row)

    row = db.execute(_SQL_GLOBAL_MODEL).mappings().first()
    if row:
        return dict(row)

    raise _model_not_found(tenant_id, project_id)


def resolve_model(
    tenant_id: str,
    project_id: Optional[str],
    db: Any,
    settings: Any,
) -> tuple[Any, float, dict]:
    """Retorna (pipeline sklearn, threshold, model_record) para o projeto.

    Usa cache LRU+TTL para evitar chamadas repetidas ao banco e ao MLflow.
    """
    cache_key = (tenant_id, project_id)
    ttl = settings.model_cache_ttl_seconds

    with _cache_lock:
        if cache_key in _cache:
            pipeline, threshold, record, loaded_at = _cache[cache_key]
            if time.time() - loaded_at < ttl:
                _cache.move_to_end(cache_key)
                return pipeline, threshold, record
            del _cache[cache_key]

    record = _query_active_model(tenant_id, project_id, db)
    mlflow_uri = f"runs:/{record['mlflow_run_id']}/model"

    logger.info("model_cache_miss", tenant_id=tenant_id, project_id=project_id, mlflow_uri=mlflow_uri)
    pipeline = mlflow.sklearn.load_model(mlflow_uri)
    threshold = float(record["threshold"])

    with _cache_lock:
        _cache[cache_key] = (pipeline, threshold, record, time.time())
        # Evicção LRU quando cache excede tamanho máximo
        if len(_cache) > _MAX_CACHE_SIZE:
            _cache.popitem(last=False)

    return pipeline, threshold, record


def invalidate_model_cache(tenant_id: str, project_id: Optional[str] = None) -> None:
    """Remove entradas do cache para forçar recarga na próxima requisição."""
    with _cache_lock:
        keys_to_remove = [
            k for k in _cache
            if k[0] == tenant_id and (project_id is None or k[1] == project_id)
        ]
        for k in keys_to_remove:
            del _cache[k]
