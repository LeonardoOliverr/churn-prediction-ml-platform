"""
Testes unitários do rate limiting por tenant.
"""

from unittest.mock import MagicMock

from src.middleware.rate_limit import _get_tenant_id, _prefix_tenant_cache


def setup_function():
    """Limpa o cache de prefixos entre testes."""
    _prefix_tenant_cache.clear()


def _make_request(api_key: str | None = None, remote_addr: str = "1.2.3.4") -> MagicMock:
    request = MagicMock()
    # Retorna string vazia quando api_key é None (comportamento correto do header ausente)
    request.headers.get = lambda key, default="": (api_key if api_key is not None else default) if key == "x-api-key" else default
    # get_remote_address(request) lê request.client.host
    request.client.host = remote_addr
    return request


def test_get_tenant_id_returns_tenant_from_cache():
    """Quando prefix (primeiros 20 chars) está no cache, retorna o tenant_id correto."""
    prefix = "churn_live_sk_aaaaXX"  # exatamente 20 chars
    _prefix_tenant_cache[prefix] = "tenant-x"

    request = _make_request(api_key=prefix + "_resto_da_key")
    result = _get_tenant_id(request)

    assert result == "tenant-x"


def test_get_tenant_id_falls_back_to_ip_when_prefix_unknown():
    """Prefix não registrado (primeira request da key) cai no fallback por IP."""
    request = _make_request(api_key="churn_live_sk_unknown_key_extra", remote_addr="9.8.7.6")
    result = _get_tenant_id(request)

    assert result == "9.8.7.6"


def test_get_tenant_id_falls_back_to_ip_when_no_api_key():
    """Requests sem x-api-key usam IP como fallback."""
    request = _make_request(api_key=None, remote_addr="5.5.5.5")
    result = _get_tenant_id(request)

    assert result == "5.5.5.5"


def test_get_tenant_id_falls_back_when_key_too_short():
    """Keys com menos de 20 caracteres não são usadas para lookup."""
    _prefix_tenant_cache["short_key_under20"] = "tenant-y"

    request = _make_request(api_key="short", remote_addr="2.2.2.2")
    result = _get_tenant_id(request)

    assert result == "2.2.2.2"


def test_prefix_tenant_cache_isolates_tenants():
    """Dois prefixes de tenants diferentes retornam tenant_ids distintos."""
    prefix_a = "churn_live_sk_tenntA"  # 20 chars
    prefix_b = "churn_live_sk_tenntB"  # 20 chars
    _prefix_tenant_cache[prefix_a] = "tenant-a"
    _prefix_tenant_cache[prefix_b] = "tenant-b"

    req_a = _make_request(api_key=prefix_a + "_extra")
    req_b = _make_request(api_key=prefix_b + "_extra")

    assert _get_tenant_id(req_a) == "tenant-a"
    assert _get_tenant_id(req_b) == "tenant-b"


def test_prefix_cache_populated_after_auth(monkeypatch):
    """get_current_api_key popula _prefix_tenant_cache após autenticação bem-sucedida."""
    from types import SimpleNamespace

    from cachetools import TTLCache

    from src.middleware.auth import ApiKeyRecord

    fake_record = ApiKeyRecord(
        id="key-id-1",
        tenant_id="tenant-populated",
        project_id="proj-1",
        scopes=["predict"],
        key_prefix="churn_live_sk_pop1",
    )

    import src.dependencies as deps

    monkeypatch.setattr(deps, "_api_key_cache", TTLCache(maxsize=256, ttl=60))
    monkeypatch.setattr(deps, "_lookup_api_key", lambda key, db: fake_record)
    monkeypatch.setattr(deps, "_update_last_used", lambda *a, **kw: None)
    monkeypatch.setattr(deps, "_get_engine", lambda *a, **kw: MagicMock())

    fake_settings = SimpleNamespace(api_key_cache_ttl_seconds=60)

    deps.get_current_api_key(
        x_api_key="churn_live_sk_pop1_full_key_rest",
        db=MagicMock(),
        settings=fake_settings,
    )

    assert _prefix_tenant_cache.get("churn_live_sk_pop1") == "tenant-populated"
