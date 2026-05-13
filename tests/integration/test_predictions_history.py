"""
Testes de integração — histórico paginado de predições.

GET /predictions?page=N&page_size=M
Requer escopo predictions:read.
"""

import uuid

import pytest
from sqlalchemy import text


def _inserir_predicao(db_conn, tenant_id, project_id, model_id, customer_id):
    """Insere predição diretamente no banco para montar histórico de teste."""
    pred_id = str(uuid.uuid4())
    db_conn.execute(
        text("""
            INSERT INTO churn.predictions
                (id, tenant_id, project_id, customer_id, model_id,
                 churn_prob, churn_pred, threshold_used)
            VALUES
                (:id, :tenant_id, :project_id, :customer_id, :model_id,
                 0.4, FALSE, 0.5)
        """),
        {
            "id": pred_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "customer_id": customer_id,
            "model_id": model_id,
        },
    )
    db_conn.commit()
    return pred_id


@pytest.mark.integration
def test_listar_predicoes_sem_historico(client, seed_api_key):
    secret, _, _ = seed_api_key
    r = client.get("/predictions", headers={"x-api-key": secret})
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


@pytest.mark.integration
def test_listar_predicoes_paginado(client, db_conn, seed_api_key, seed_model):
    secret, tenant_id, project_id = seed_api_key

    for i in range(5):
        _inserir_predicao(db_conn, tenant_id, project_id, seed_model, f"hist-{i}")

    r = client.get("/predictions?page_size=3", headers={"x-api-key": secret})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 3


@pytest.mark.integration
def test_listar_predicoes_pagina_dois(client, db_conn, seed_api_key, seed_model):
    secret, tenant_id, project_id = seed_api_key

    for i in range(5):
        _inserir_predicao(db_conn, tenant_id, project_id, seed_model, f"pag2-{i}")

    r = client.get("/predictions?page=2&page_size=3", headers={"x-api-key": secret})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["page"] == 2


@pytest.mark.integration
def test_listar_predicoes_campos_da_resposta(client, db_conn, seed_api_key, seed_model):
    secret, tenant_id, project_id = seed_api_key
    _inserir_predicao(db_conn, tenant_id, project_id, seed_model, "campo-check")

    r = client.get("/predictions", headers={"x-api-key": secret})
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert "id" in item
    assert "customer_id" in item
    assert "churn_probability" in item
    assert "churn_pred" in item
    assert "threshold_used" in item
    assert "requested_at" in item
    assert "model_id" in item


@pytest.mark.integration
def test_listar_predicoes_sem_escopo_retorna_403(client, db_conn, seed_tenant, seed_project):
    """Key com apenas 'predict' não pode chamar GET /predictions."""
    import bcrypt

    secret = "churn_live_sk_noreadscopekey000000000000"
    key_hash = bcrypt.hashpw(secret.encode(), bcrypt.gensalt(rounds=4)).decode()
    db_conn.execute(
        text("""
            INSERT INTO churn.api_keys
                (tenant_id, project_id, key_hash, key_prefix, scopes, is_active)
            VALUES
                (:tenant_id, :project_id, :key_hash, :key_prefix,
                 ARRAY['predict'], TRUE)
        """),
        {
            "tenant_id": seed_tenant,
            "project_id": seed_project,
            "key_hash": key_hash,
            "key_prefix": secret[:20],
        },
    )
    db_conn.commit()

    r = client.get("/predictions", headers={"x-api-key": secret})
    assert r.status_code == 403
