"""
Testes de integração — predição individual e em lote.

Pré-condição: seed_champion configura um champion com pipeline mock e
              seed_api_key cria uma API key válida para o mesmo tenant/projeto.
"""

import pytest
from sqlalchemy import text

from tests.integration.conftest import MINIMAL_PAYLOAD

# ---------------------------------------------------------------------------
# Predição individual
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_predict_retorna_estrutura_correta(client, seed_api_key, seed_champion):
    secret, _, _ = seed_api_key
    r = client.post("/predict", json=MINIMAL_PAYLOAD, headers={"x-api-key": secret})

    assert r.status_code == 200
    body = r.json()
    assert "churn_probability" in body
    assert "risk_level" in body
    assert "prediction_id" in body
    assert "model_id" in body
    assert 0.0 <= body["churn_probability"] <= 1.0
    assert body["risk_level"] in ("low", "medium", "high")


@pytest.mark.integration
def test_predict_grava_no_banco(client, db_conn, seed_api_key, seed_champion):
    """
    Verifica que a predição é persistida em churn.predictions pelo background task.
    O TestClient executa background tasks antes de retornar a resposta.
    """
    secret, _, _ = seed_api_key
    r = client.post("/predict", json=MINIMAL_PAYLOAD, headers={"x-api-key": secret})
    assert r.status_code == 200

    pred_id = r.json()["prediction_id"]
    row = db_conn.execute(
        text("SELECT id FROM churn.predictions WHERE id = :id"),
        {"id": pred_id},
    ).first()
    assert row is not None, "Predição não foi gravada em churn.predictions"


@pytest.mark.integration
def test_predict_modelo_nao_configurado(client, seed_api_key):
    """Projeto sem champion configurado deve retornar 404 model_not_found."""
    secret, _, _ = seed_api_key
    r = client.post("/predict", json=MINIMAL_PAYLOAD, headers={"x-api-key": secret})

    assert r.status_code == 404
    assert r.json()["error"] == "model_not_found"


@pytest.mark.integration
def test_predict_payload_invalido(client, seed_api_key, seed_champion):
    secret, _, _ = seed_api_key
    r = client.post(
        "/predict",
        json={"tenure_months": "nao_e_numero"},
        headers={"x-api-key": secret},
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_predict_campo_obrigatorio_ausente(client, seed_api_key, seed_champion):
    secret, _, _ = seed_api_key
    payload_incompleto = {k: v for k, v in MINIMAL_PAYLOAD.items() if k != "contract"}
    r = client.post("/predict", json=payload_incompleto, headers={"x-api-key": secret})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Predição em lote
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_batch_predict_retorna_lista_ordenada(client, seed_api_key, seed_champion):
    secret, _, _ = seed_api_key
    customers = [{**MINIMAL_PAYLOAD, "customer_id": f"c-{i}"} for i in range(5)]
    r = client.post(
        "/predict/batch",
        json={"customers": customers},
        headers={"x-api-key": secret},
    )
    assert r.status_code == 200
    body = r.json()
    results = body["results"]
    assert len(results) == 5
    assert [p["customer_id"] for p in results] == [f"c-{i}" for i in range(5)]
    assert body["total"] == 5


@pytest.mark.integration
def test_batch_acima_do_limite(client, seed_api_key, seed_champion):
    secret, _, _ = seed_api_key
    customers = [{**MINIMAL_PAYLOAD, "customer_id": f"c-{i}"} for i in range(101)]
    r = client.post(
        "/predict/batch",
        json={"customers": customers},
        headers={"x-api-key": secret},
    )
    assert r.status_code == 422
    assert "batch_too_large" in r.text


@pytest.mark.integration
def test_batch_vazio(client, seed_api_key, seed_champion):
    secret, _, _ = seed_api_key
    r = client.post(
        "/predict/batch",
        json={"customers": []},
        headers={"x-api-key": secret},
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_batch_sem_api_key(client, seed_champion):
    customers = [MINIMAL_PAYLOAD]
    r = client.post("/predict/batch", json={"customers": customers})
    assert r.status_code == 401
