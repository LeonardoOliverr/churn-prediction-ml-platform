"""
Testes unitários dos caminhos de erro do health router.

Cobre os ramos `except` que os testes de integração não alcançam:
- _check_database: exceção na conexão → status "error"
- _check_mlflow: timeout / recusa de conexão → status "error"
- /health/ready: retorno 503 quando dependência falha
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.routers.health import _check_database, _check_mlflow
from src.schemas.health import CheckResult

# ---------------------------------------------------------------------------
# _check_database
# ---------------------------------------------------------------------------


def test_check_database_ok():
    """Conexão bem-sucedida retorna status ok e latência não-nula."""
    db = MagicMock()
    result = _check_database(db)
    assert result.status == "ok"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_check_database_failure_returns_error_status():
    """Exceção na execução do SELECT 1 retorna status error e latency_ms None."""
    db = MagicMock()
    db.execute.side_effect = Exception("connection refused")
    result = _check_database(db)
    assert result.status == "error"
    assert result.latency_ms is None


# ---------------------------------------------------------------------------
# _check_mlflow
# ---------------------------------------------------------------------------


def test_check_mlflow_success():
    """Endpoint /health acessível retorna status ok e latência não-nula."""
    mock_resp = MagicMock()
    mock_resp.close.return_value = None
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _check_mlflow("http://localhost:5000")
    assert result.status == "ok"
    assert result.latency_ms is not None


def test_check_mlflow_failure_returns_error_status():
    """Falha de conexão ao MLflow retorna status error e latency_ms None."""
    with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
        result = _check_mlflow("http://localhost:5000")
    assert result.status == "error"
    assert result.latency_ms is None


def test_check_mlflow_strips_trailing_slash():
    """Trailing slash na URI é removida antes de appender /health."""
    mock_resp = MagicMock()
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        _check_mlflow("http://localhost:5000/")
    called_url = mock_open.call_args[0][0]
    assert called_url == "http://localhost:5000/health"


# ---------------------------------------------------------------------------
# /health/ready → 503 degraded
# ---------------------------------------------------------------------------


def test_health_ready_returns_503_when_all_checks_fail():
    """503 é retornado e status é 'degraded' quando banco e MLflow falham."""
    from src.dependencies import get_db
    from src.main import app

    error_check = CheckResult(status="error", latency_ms=None)

    def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with (
            patch("src.routers.health._check_database", return_value=error_check),
            patch("src.routers.health._check_mlflow", return_value=error_check),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                r = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"]["status"] == "error"
    assert body["checks"]["mlflow"]["status"] == "error"


def test_health_ready_degraded_checks_have_null_latency():
    """Checks com erro reportam latency_ms nulo."""
    from src.dependencies import get_db
    from src.main import app

    error_check = CheckResult(status="error", latency_ms=None)

    def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with (
            patch("src.routers.health._check_database", return_value=error_check),
            patch("src.routers.health._check_mlflow", return_value=error_check),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                r = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    body = r.json()
    assert body["checks"]["database"]["latency_ms"] is None
    assert body["checks"]["mlflow"]["latency_ms"] is None


def test_health_ready_returns_200_when_all_checks_ok():
    """200 é retornado quando todos os checks passam."""
    from src.dependencies import get_db
    from src.main import app

    ok_check = CheckResult(status="ok", latency_ms=5)

    def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with (
            patch("src.routers.health._check_database", return_value=ok_check),
            patch("src.routers.health._check_mlflow", return_value=ok_check),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                r = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    assert r.json()["status"] == "ready"
