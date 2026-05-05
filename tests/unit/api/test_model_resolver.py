"""
Testes unitários do roteamento champion/challenger.
"""

from types import SimpleNamespace
from unittest.mock import patch

from src.services import model_resolver


def setup_function():
    """Limpa cache entre testes para evitar vazamento de estado."""
    model_resolver._cache.clear()


def _record(model_id: str, role: str, split: float = 0.0) -> dict:
    """Cria registro mínimo retornado pelo resolver."""
    return {
        "id": model_id,
        "mlflow_run_id": f"run-{model_id}",
        "version": "v1",
        "name": f"model-{model_id}",
        "role": role,
        "threshold": 0.5,
        "traffic_split": split,
        "tenant_id": "tenant-1",
        "project_id": "project-1",
    }


def test_resolve_model_without_challenger_serves_champion():
    """Sem challenger ativo, sempre serve champion."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)
    champion = _record("champion-id", "champion")
    pipeline = object()

    with patch("src.services.model_resolver._query_serving_candidates", return_value=(champion, None)), \
         patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=pipeline):
        resolved_pipeline, threshold, record = model_resolver.resolve_model(
            tenant_id="tenant-1",
            project_id="project-1",
            db=object(),
            settings=settings,
            customer_id="CUST-1",
        )

    assert resolved_pipeline is pipeline
    assert threshold == 0.5
    assert record["id"] == "champion-id"


def test_resolve_model_routes_to_challenger_when_bucket_is_inside_split():
    """Bucket menor que traffic_split envia o cliente ao challenger."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)
    champion = _record("champion-id", "champion")
    challenger = _record("challenger-id", "challenger", split=0.2)

    with patch("src.services.model_resolver._query_serving_candidates", return_value=(champion, challenger)), \
         patch("src.services.model_resolver._traffic_bucket", return_value=0.1), \
         patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()):
        _, _, record = model_resolver.resolve_model(
            tenant_id="tenant-1",
            project_id="project-1",
            db=object(),
            settings=settings,
            customer_id="CUST-2",
        )

    assert record["id"] == "challenger-id"


def test_traffic_bucket_is_stable_for_same_customer():
    """Hash determinístico mantém o mesmo cliente no mesmo bucket."""
    first = model_resolver._traffic_bucket("tenant-1", "project-1", "CUST-42")
    second = model_resolver._traffic_bucket("tenant-1", "project-1", "CUST-42")

    assert first == second
    assert 0 <= first <= 1


def test_cache_key_separates_champion_and_challenger():
    """Champion e challenger usam entradas de cache independentes."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)
    champion = _record("champion-id", "champion")
    challenger = _record("challenger-id", "challenger", split=0.2)

    with patch("src.services.model_resolver._query_serving_candidates", return_value=(champion, challenger)), \
         patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()) as mock_load:
        with patch("src.services.model_resolver._traffic_bucket", return_value=0.9):
            model_resolver.resolve_model("tenant-1", "project-1", object(), settings, customer_id="A")
        with patch("src.services.model_resolver._traffic_bucket", return_value=0.1):
            model_resolver.resolve_model("tenant-1", "project-1", object(), settings, customer_id="B")

    assert mock_load.call_count == 2
    assert ("tenant-1", "project-1", "champion", "champion-id") in model_resolver._cache
    assert ("tenant-1", "project-1", "challenger", "challenger-id") in model_resolver._cache
