"""
Testes de integração — isolamento multi-tenant.

Garante que dados de um tenant nunca vazam para outro tenant via API.
Estratégia: insere predições diretamente no banco para o tenant A e
verifica que o tenant B vê lista vazia.
"""

import uuid

import bcrypt
import pytest
from sqlalchemy import text


def _criar_tenant_completo(db_conn, suffix: str):
    """Cria tenant + projeto + API key com escopo predictions:read. Retorna (key, tenant_id, project_id)."""
    tenant_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    secret = f"churn_live_sk_{suffix}_{'0' * 25}"  # prefixo [:20] único por suffix

    db_conn.execute(
        text("INSERT INTO churn.tenants (id, name, slug) VALUES (:id, :name, :slug)"),
        {"id": tenant_id, "name": f"Tenant {suffix}", "slug": f"tenant-{suffix}"},
    )
    db_conn.execute(
        text("""
            INSERT INTO churn.projects (id, tenant_id, name, slug)
            VALUES (:id, :tenant_id, :name, :slug)
        """),
        {
            "id": project_id,
            "tenant_id": tenant_id,
            "name": f"Proj {suffix}",
            "slug": f"proj-{suffix}",
        },
    )
    key_hash = bcrypt.hashpw(secret.encode(), bcrypt.gensalt(rounds=4)).decode()
    db_conn.execute(
        text("""
            INSERT INTO churn.api_keys
                (tenant_id, project_id, key_hash, key_prefix, scopes, is_active)
            VALUES
                (:tenant_id, :project_id, :key_hash, :key_prefix,
                 ARRAY['predict', 'predictions:read'], TRUE)
        """),
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "key_hash": key_hash,
            "key_prefix": secret[:20],
        },
    )
    db_conn.commit()
    return secret, tenant_id, project_id


def _inserir_predicao(db_conn, tenant_id, project_id, model_id, customer_id):
    """Insere uma predição diretamente no banco para simular histórico."""
    pred_id = str(uuid.uuid4())
    db_conn.execute(
        text("""
            INSERT INTO churn.predictions
                (id, tenant_id, project_id, customer_id, model_id,
                 churn_prob, churn_pred, threshold_used)
            VALUES
                (:id, :tenant_id, :project_id, :customer_id, :model_id,
                 0.3, FALSE, 0.5)
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
def test_predicoes_do_tenant_a_nao_aparecem_para_tenant_b(client, db_conn, seed_model):
    key_a, tenant_a, project_a = _criar_tenant_completo(db_conn, "aaa")
    key_b, tenant_b, project_b = _criar_tenant_completo(db_conn, "bbb")

    # Insere predição para tenant A
    _inserir_predicao(db_conn, tenant_a, project_a, seed_model, "cliente-secreto-a")

    # Tenant A vê sua própria predição
    r_a = client.get("/predictions", headers={"x-api-key": key_a})
    assert r_a.status_code == 200
    ids_a = [p["customer_id"] for p in r_a.json()["items"]]
    assert "cliente-secreto-a" in ids_a

    # Tenant B não vê a predição do tenant A
    r_b = client.get("/predictions", headers={"x-api-key": key_b})
    assert r_b.status_code == 200
    ids_b = [p["customer_id"] for p in r_b.json()["items"]]
    assert "cliente-secreto-a" not in ids_b


@pytest.mark.integration
def test_key_de_tenant_a_nao_acessa_admin_do_tenant_b(client, db_conn, admin_headers):
    key_a, tenant_a, _ = _criar_tenant_completo(db_conn, "ccc")
    _, tenant_b, _ = _criar_tenant_completo(db_conn, "ddd")

    # Tenta usar API key do tenant A como Bearer para acessar admin de tenant B
    r = client.get(
        f"/admin/tenants/{tenant_b}/keys",
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert r.status_code == 401


@pytest.mark.integration
def test_dois_tenants_com_predicoes_proprias(client, db_conn, seed_model):
    key_a, tenant_a, project_a = _criar_tenant_completo(db_conn, "eee")
    key_b, tenant_b, project_b = _criar_tenant_completo(db_conn, "fff")

    # Cada tenant tem suas próprias predições
    _inserir_predicao(db_conn, tenant_a, project_a, seed_model, "cliente-a-001")
    _inserir_predicao(db_conn, tenant_a, project_a, seed_model, "cliente-a-002")
    _inserir_predicao(db_conn, tenant_b, project_b, seed_model, "cliente-b-001")

    r_a = client.get("/predictions", headers={"x-api-key": key_a})
    r_b = client.get("/predictions", headers={"x-api-key": key_b})

    ids_a = {p["customer_id"] for p in r_a.json()["items"]}
    ids_b = {p["customer_id"] for p in r_b.json()["items"]}

    assert ids_a == {"cliente-a-001", "cliente-a-002"}
    assert ids_b == {"cliente-b-001"}
