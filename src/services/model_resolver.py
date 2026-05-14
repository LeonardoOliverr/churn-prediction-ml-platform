"""
Resolução de modelo em produção por projeto com cache LRU+TTL.

`churn.models.status` define elegibilidade técnica. Somente modelos `approved`
podem ser servidos. `churn.project_model_config` define a configuração
operacional: champion, challenger, threshold, split de tráfego e ativação.
"""

import hashlib
import time
from collections import OrderedDict
from threading import Lock
from typing import Any

import mlflow.sklearn
import structlog
from sqlalchemy import text

from domain.exceptions import ModelNotFoundError

logger = structlog.get_logger()

# Cache LRU+TTL: chave (tenant_id, project_id, role, model_id) -> (pipeline, threshold, record, loaded_at)
_cache: OrderedDict = OrderedDict()
_cache_lock = Lock()
_MAX_CACHE_SIZE = 128

_MODEL_SELECT_FIELDS = """
    m.id,
    m.mlflow_run_id,
    m.version,
    m.name,
    m.tenant_id AS model_tenant_id,
    m.project_id AS model_project_id,
    pmc.tenant_id,
    pmc.project_id,
    pmc.role,
    COALESCE(pmc.threshold, 0.5) AS threshold,
    COALESCE(pmc.traffic_split, 0) AS traffic_split
"""

_SQL_PROJECT_MODEL_BY_ROLE = text(f"""
    SELECT {_MODEL_SELECT_FIELDS}
    FROM churn.project_model_config pmc
    JOIN churn.models m ON m.id = pmc.model_id
    WHERE pmc.tenant_id    = :tenant_id
      AND pmc.project_id   = :project_id
      AND pmc.environment  = 'production'
      AND pmc.is_active    = TRUE
      AND pmc.role         = :role
      AND m.status         = 'approved'
    ORDER BY pmc.configured_at DESC, pmc.id DESC
    LIMIT 1
""")


def _model_not_found(tenant_id: str, project_id: str) -> ModelNotFoundError:
    """Cria erro de domínio quando não há modelo de produção configurado."""
    return ModelNotFoundError(
        f"Nenhum modelo aprovado em produção encontrado "
        f"para tenant_id={tenant_id} e project_id={project_id}"
    )


def _query_project_model_by_role(tenant_id: str, project_id: str, role: str, db) -> dict | None:
    """Busca champion ou challenger ativo do projeto."""
    row = (
        db.execute(
            _SQL_PROJECT_MODEL_BY_ROLE,
            {"tenant_id": tenant_id, "project_id": project_id, "role": role},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def _query_serving_candidates(
    tenant_id: str,
    project_id: str,
    db,
) -> tuple[dict, dict | None]:
    """Retorna (champion, challenger) do projeto. Erro 404 explícito se não configurado."""
    champion = _query_project_model_by_role(tenant_id, project_id, "champion", db)
    challenger = _query_project_model_by_role(tenant_id, project_id, "challenger", db)

    if champion is None:
        raise _model_not_found(tenant_id, project_id)

    return champion, challenger


def _traffic_bucket(tenant_id: str, project_id: str, customer_id: str) -> float:
    """Calcula bucket determinístico entre 0 e 1 para roteamento de tráfego."""
    key = f"{tenant_id}:{project_id}:{customer_id}".encode()
    digest = hashlib.sha256(key).hexdigest()
    return int(digest[:16], 16) / float(2**64)


def _choose_record(
    tenant_id: str,
    project_id: str,
    customer_id: str | None,
    champion: dict,
    challenger: dict | None,
) -> dict:
    """Escolhe champion ou challenger conforme split determinístico."""
    if challenger is None or customer_id is None:
        return champion

    traffic_split = float(challenger.get("traffic_split") or 0)
    if traffic_split <= 0:
        return champion

    if _traffic_bucket(tenant_id, project_id, customer_id) < traffic_split:
        return challenger

    return champion


def _load_pipeline(record: dict, cache_key: tuple, ttl: int) -> tuple[Any, float, dict]:
    """Carrega pipeline do MLflow usando cache LRU+TTL."""
    with _cache_lock:
        if cache_key in _cache:
            pipeline, threshold, cached_record, loaded_at = _cache[cache_key]
            if time.time() - loaded_at < ttl:
                _cache.move_to_end(cache_key)
                return pipeline, threshold, cached_record
            del _cache[cache_key]

    mlflow_uri = f"runs:/{record['mlflow_run_id']}/model"
    logger.info(
        "model_cache_miss",
        tenant_id=str(record.get("tenant_id")),
        project_id=str(record.get("project_id")),
        role=record.get("role"),
        model_id=str(record.get("id")),
        mlflow_uri=mlflow_uri,
    )
    pipeline = mlflow.sklearn.load_model(mlflow_uri)
    threshold = float(record["threshold"])

    with _cache_lock:
        _cache[cache_key] = (pipeline, threshold, record, time.time())
        if len(_cache) > _MAX_CACHE_SIZE:
            _cache.popitem(last=False)

    return pipeline, threshold, record


def resolve_model(
    tenant_id: str,
    project_id: str,
    db: Any,
    settings: Any,
    customer_id: str | None = None,
) -> tuple[Any, float, dict]:
    """Retorna (pipeline sklearn, threshold, model_record) para a predição."""
    champion, challenger = _query_serving_candidates(tenant_id, project_id, db)
    record = _choose_record(tenant_id, project_id, customer_id, champion, challenger)
    cache_key = (tenant_id, project_id, record["role"], str(record["id"]))
    return _load_pipeline(record, cache_key, settings.model_cache_ttl_seconds)


def resolve_batch_models(
    tenant_id: str,
    project_id: str,
    db: Any,
    settings: Any,
) -> tuple[tuple[Any, float, dict], tuple[Any, float, dict] | None]:
    """Carrega champion e challenger uma única vez para inferência em lote."""
    champion_record, challenger_record = _query_serving_candidates(tenant_id, project_id, db)

    champion_key = (tenant_id, project_id, "champion", str(champion_record["id"]))
    champion_loaded = _load_pipeline(
        champion_record, champion_key, settings.model_cache_ttl_seconds
    )

    if challenger_record is None:
        return champion_loaded, None

    challenger_key = (tenant_id, project_id, "challenger", str(challenger_record["id"]))
    challenger_loaded = _load_pipeline(
        challenger_record, challenger_key, settings.model_cache_ttl_seconds
    )

    return champion_loaded, challenger_loaded


def choose_for_customer(
    tenant_id: str,
    project_id: str,
    customer_id: str | None,
    champion_loaded: tuple[Any, float, dict],
    challenger_loaded: tuple[Any, float, dict] | None,
) -> tuple[Any, float, dict]:
    """Seleciona champion ou challenger para um cliente, sem consultar o banco."""
    if challenger_loaded is None or customer_id is None:
        return champion_loaded

    _, _, challenger_record = challenger_loaded
    traffic_split = float(challenger_record.get("traffic_split") or 0)
    if traffic_split <= 0:
        return champion_loaded

    if _traffic_bucket(tenant_id, project_id, customer_id) < traffic_split:
        return challenger_loaded

    return champion_loaded


def invalidate_model_cache(tenant_id: str, project_id: str | None = None) -> None:
    """Remove entradas do cache para forçar recarga na próxima requisição."""
    with _cache_lock:
        keys_to_remove = [
            key
            for key in _cache
            if key[0] == tenant_id and (project_id is None or key[1] == project_id)
        ]
        for key in keys_to_remove:
            del _cache[key]
