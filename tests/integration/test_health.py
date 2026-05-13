"""
Testes de integração — probes de infraestrutura.

GET /health      → liveness (sempre 200 enquanto o processo estiver vivo)
GET /health/ready → readiness (verifica banco; MLflow pode estar offline em CI)
"""

import pytest


@pytest.mark.integration
def test_health_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "timestamp" in body


@pytest.mark.integration
def test_health_ready_banco_ok(client):
    r = client.get("/health/ready")
    body = r.json()
    # Banco de teste deve responder; MLflow pode estar offline — verificamos só o DB
    assert "checks" in body
    assert body["checks"]["database"]["status"] == "ok"


@pytest.mark.integration
def test_health_ready_campos_presentes(client):
    r = client.get("/health/ready")
    body = r.json()
    assert "status" in body
    assert "timestamp" in body
    assert "checks" in body
    assert "database" in body["checks"]
    assert "mlflow" in body["checks"]
