"""
Testes unitários do roteamento champion/challenger.
"""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from domain.exceptions import ModelNotFoundError
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

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates", return_value=(champion, None)
        ),
        patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=pipeline),
    ):
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

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates",
            return_value=(champion, challenger),
        ),
        patch("src.services.model_resolver._traffic_bucket", return_value=0.1),
        patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()),
    ):
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

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates",
            return_value=(champion, challenger),
        ),
        patch(
            "src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()
        ) as mock_load,
    ):
        with patch("src.services.model_resolver._traffic_bucket", return_value=0.9):
            model_resolver.resolve_model(
                "tenant-1", "project-1", object(), settings, customer_id="A"
            )
        with patch("src.services.model_resolver._traffic_bucket", return_value=0.1):
            model_resolver.resolve_model(
                "tenant-1", "project-1", object(), settings, customer_id="B"
            )

    assert mock_load.call_count == 2
    assert ("tenant-1", "project-1", "champion", "champion-id") in model_resolver._cache
    assert ("tenant-1", "project-1", "challenger", "challenger-id") in model_resolver._cache


# ---------------------------------------------------------------------------
# Funções de query — cobertura das linhas de DB
# ---------------------------------------------------------------------------


def test_query_project_model_by_role_returns_dict_when_row_found():
    """Retorna dict quando a query encontra um registro."""
    mock_row = {"id": "m1", "role": "champion", "threshold": 0.5, "traffic_split": 0.0}
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = mock_row

    result = model_resolver._query_project_model_by_role("tenant-1", "project-1", "champion", db)

    assert result == mock_row


def test_query_project_model_by_role_returns_none_when_no_row():
    """Retorna None quando nenhum modelo está configurado."""
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = None

    result = model_resolver._query_project_model_by_role("tenant-1", "project-1", "champion", db)

    assert result is None


def test_query_serving_candidates_raises_404_when_no_champion():
    """Projeto sem champion configurado levanta ModelNotFoundError."""
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = None

    with pytest.raises(ModelNotFoundError):
        model_resolver._query_serving_candidates("tenant-1", "project-1", db)


# ---------------------------------------------------------------------------
# Cache TTL
# ---------------------------------------------------------------------------


def test_cache_hit_within_ttl_skips_mlflow():
    """Segunda chamada dentro do TTL não chama mlflow.sklearn.load_model."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)
    champion = _record("champion-id", "champion")
    pipeline = object()

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates", return_value=(champion, None)
        ),
        patch(
            "src.services.model_resolver.mlflow.sklearn.load_model", return_value=pipeline
        ) as mock_load,
    ):
        model_resolver.resolve_model("tenant-1", "project-1", object(), settings)
        model_resolver.resolve_model("tenant-1", "project-1", object(), settings)

    assert mock_load.call_count == 1


def test_cache_expired_reloads_from_mlflow():
    """Entrada expirada (TTL=0) recarrega do MLflow na próxima chamada."""
    settings = SimpleNamespace(model_cache_ttl_seconds=0)
    champion = _record("champion-id", "champion")

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates", return_value=(champion, None)
        ),
        patch(
            "src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()
        ) as mock_load,
    ):
        model_resolver.resolve_model("tenant-t", "project-p", object(), settings)
        model_resolver.resolve_model("tenant-t", "project-p", object(), settings)

    assert mock_load.call_count == 2


# ---------------------------------------------------------------------------
# _choose_record — traffic_split <= 0
# ---------------------------------------------------------------------------


def test_choose_record_challenger_with_zero_split_returns_champion():
    """Challenger com traffic_split=0 é ignorado — retorna champion."""
    champion = _record("champion-id", "champion")
    challenger = _record("challenger-id", "challenger", split=0.0)

    result = model_resolver._choose_record("tenant-1", "project-1", "CUST-1", champion, challenger)

    assert result["id"] == "champion-id"


def test_choose_record_no_customer_id_returns_champion():
    """customer_id=None força retorno do champion independente do challenger."""
    champion = _record("champion-id", "champion")
    challenger = _record("challenger-id", "challenger", split=0.5)

    result = model_resolver._choose_record("tenant-1", "project-1", None, champion, challenger)

    assert result["id"] == "champion-id"


def test_query_serving_candidates_returns_champion_and_challenger():
    """Retorna (champion, challenger) quando ambos estão configurados no projeto."""
    champion = _record("champion-id", "champion")
    challenger = _record("challenger-id", "challenger", split=0.2)

    def _by_role(tenant_id, project_id, role, db):
        return champion if role == "champion" else challenger

    with patch("src.services.model_resolver._query_project_model_by_role", side_effect=_by_role):
        champ, chal = model_resolver._query_serving_candidates("tenant-1", "project-1", MagicMock())

    assert champ["id"] == "champion-id"
    assert chal["id"] == "challenger-id"


# ---------------------------------------------------------------------------
# invalidate_model_cache
# ---------------------------------------------------------------------------


def test_invalidate_model_cache_removes_all_tenant_entries():
    """invalidate_model_cache remove todas as entradas do tenant especificado."""
    model_resolver._cache[("tenant-x", "proj-1", "champion", "m1")] = (object(), 0.5, {}, 0)
    model_resolver._cache[("tenant-x", "proj-2", "champion", "m2")] = (object(), 0.5, {}, 0)
    model_resolver._cache[("tenant-y", "proj-1", "champion", "m3")] = (object(), 0.5, {}, 0)

    model_resolver.invalidate_model_cache("tenant-x")

    assert ("tenant-x", "proj-1", "champion", "m1") not in model_resolver._cache
    assert ("tenant-x", "proj-2", "champion", "m2") not in model_resolver._cache
    assert ("tenant-y", "proj-1", "champion", "m3") in model_resolver._cache


def test_invalidate_model_cache_with_project_id_removes_only_that_project():
    """project_id restrito remove somente o projeto especificado."""
    model_resolver._cache[("tenant-x", "proj-1", "champion", "m1")] = (object(), 0.5, {}, 0)
    model_resolver._cache[("tenant-x", "proj-2", "champion", "m2")] = (object(), 0.5, {}, 0)

    model_resolver.invalidate_model_cache("tenant-x", project_id="proj-1")

    assert ("tenant-x", "proj-1", "champion", "m1") not in model_resolver._cache
    assert ("tenant-x", "proj-2", "champion", "m2") in model_resolver._cache


# ---------------------------------------------------------------------------
# choose_for_customer
# ---------------------------------------------------------------------------


def test_choose_for_customer_no_challenger_returns_champion_tuple():
    """Sem challenger carregado, retorna a tupla de champion."""
    champion_loaded = (object(), 0.5, _record("champion-id", "champion"))

    result = model_resolver.choose_for_customer(
        "tenant-1", "project-1", "CUST-1", champion_loaded, None
    )

    assert result is champion_loaded


def test_choose_for_customer_routes_to_challenger():
    """Roteamento ao challenger quando bucket < traffic_split."""
    champion_loaded = (object(), 0.5, _record("champion-id", "champion"))
    challenger_loaded = (object(), 0.5, _record("challenger-id", "challenger", split=0.5))

    with patch("src.services.model_resolver._traffic_bucket", return_value=0.1):
        result = model_resolver.choose_for_customer(
            "tenant-1", "project-1", "CUST-1", champion_loaded, challenger_loaded
        )

    assert result is challenger_loaded


def test_choose_for_customer_zero_split_returns_champion():
    """traffic_split=0 no challenger sempre retorna champion."""
    champion_loaded = (object(), 0.5, _record("champion-id", "champion"))
    challenger_loaded = (object(), 0.5, _record("challenger-id", "challenger", split=0.0))

    result = model_resolver.choose_for_customer(
        "tenant-1", "project-1", "CUST-1", champion_loaded, challenger_loaded
    )

    assert result is champion_loaded


# ---------------------------------------------------------------------------
# resolve_batch_models
# ---------------------------------------------------------------------------


def test_resolve_batch_models_loads_both_champion_and_challenger():
    """resolve_batch_models retorna dois pipelines quando há challenger."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)
    champion = _record("champion-id", "champion")
    challenger = _record("challenger-id", "challenger", split=0.2)

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates",
            return_value=(champion, challenger),
        ),
        patch(
            "src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()
        ) as mock_load,
    ):
        champ_t, chal_t = model_resolver.resolve_batch_models(
            "tenant-1", "project-1", object(), settings
        )

    assert mock_load.call_count == 2
    assert chal_t is not None
    assert champ_t[2]["id"] == "champion-id"
    assert chal_t[2]["id"] == "challenger-id"


def test_resolve_batch_models_returns_none_challenger_when_absent():
    """resolve_batch_models retorna (champion, None) sem challenger configurado."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)
    champion = _record("champion-id", "champion")

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates", return_value=(champion, None)
        ),
        patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()),
    ):
        champ_t, chal_t = model_resolver.resolve_batch_models(
            "tenant-1", "project-1", object(), settings
        )

    assert chal_t is None
    assert champ_t[2]["id"] == "champion-id"


# ---------------------------------------------------------------------------
# Cache eviction (LRU)
# ---------------------------------------------------------------------------


def test_cache_eviction_when_max_size_exceeded():
    """Cache descarta a entrada LRU quando ultrapassa _MAX_CACHE_SIZE."""
    settings = SimpleNamespace(model_cache_ttl_seconds=300)

    for i in range(model_resolver._MAX_CACHE_SIZE):
        model_resolver._cache[(f"tenant-evict-{i}", f"proj-{i}", "champion", f"m{i}")] = (
            object(),
            0.5,
            {},
            time.time(),
        )

    assert len(model_resolver._cache) == model_resolver._MAX_CACHE_SIZE

    new_champion = _record("new-id", "champion")
    new_champion["tenant_id"] = "tenant-new"
    new_champion["project_id"] = "project-new"

    with (
        patch(
            "src.services.model_resolver._query_serving_candidates",
            return_value=(new_champion, None),
        ),
        patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=object()),
    ):
        model_resolver.resolve_model("tenant-new", "project-new", object(), settings)

    assert len(model_resolver._cache) == model_resolver._MAX_CACHE_SIZE
