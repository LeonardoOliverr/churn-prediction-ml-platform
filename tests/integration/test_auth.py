"""
Testes de integração — autenticação e autorização.

Cobre:
- API key: ausente, inválida, revogada, expirada, escopo insuficiente
- JWT admin: ausente, assinatura inválida, expirado
"""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlalchemy import text

from tests.integration.conftest import MINIMAL_PAYLOAD, TEST_SECRET_KEY

# ---------------------------------------------------------------------------
# API Key — casos de falha
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_predict_sem_api_key(client):
    r = client.post("/predict", json=MINIMAL_PAYLOAD)
    assert r.status_code == 401


@pytest.mark.integration
def test_predict_api_key_invalida(client):
    r = client.post(
        "/predict",
        json=MINIMAL_PAYLOAD,
        headers={"x-api-key": "churn_live_sk_tokeninvalido0000000000000"},
    )
    assert r.status_code == 401


@pytest.mark.integration
def test_predict_key_revogada(client, db_conn, seed_api_key):
    secret, _, _ = seed_api_key
    db_conn.execute(
        text("UPDATE churn.api_keys SET is_active = FALSE WHERE key_prefix = :p"),
        {"p": secret[:20]},
    )
    db_conn.commit()

    r = client.post("/predict", json=MINIMAL_PAYLOAD, headers={"x-api-key": secret})
    assert r.status_code == 401


@pytest.mark.integration
def test_predict_key_expirada(client, db_conn, seed_tenant, seed_project):
    import bcrypt

    secret = "churn_live_sk_expiredkey000000000000000"
    key_hash = bcrypt.hashpw(secret.encode(), bcrypt.gensalt(rounds=4)).decode()
    expires_passado = datetime(2000, 1, 1, tzinfo=timezone.utc)

    db_conn.execute(
        text("""
            INSERT INTO churn.api_keys
                (tenant_id, project_id, key_hash, key_prefix, scopes, is_active, expires_at)
            VALUES
                (:tenant_id, :project_id, :key_hash, :key_prefix,
                 ARRAY['predict'], TRUE, :expires_at)
        """),
        {
            "tenant_id": seed_tenant,
            "project_id": seed_project,
            "key_hash": key_hash,
            "key_prefix": secret[:20],
            "expires_at": expires_passado,
        },
    )
    db_conn.commit()

    r = client.post("/predict", json=MINIMAL_PAYLOAD, headers={"x-api-key": secret})
    assert r.status_code == 401


@pytest.mark.integration
def test_escopo_insuficiente_predictions(client, db_conn, seed_tenant, seed_project):
    """Key com apenas escopo 'predict' não pode acessar GET /predictions."""
    import bcrypt

    secret = "churn_live_sk_readonlykey00000000000000"
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
    assert r.json()["detail"]["error"] == "scope_insufficient"


# ---------------------------------------------------------------------------
# JWT Admin — casos de falha
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_admin_sem_jwt(client):
    r = client.post("/admin/tenants", json={"name": "X", "slug": "x"})
    assert r.status_code == 401


@pytest.mark.integration
def test_admin_jwt_assinatura_invalida(client):
    payload = {
        "sub": "admin",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, "chave-errada", algorithm="HS256")
    r = client.post(
        "/admin/tenants",
        json={"name": "X", "slug": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


@pytest.mark.integration
def test_admin_jwt_expirado(client):
    payload = {
        "sub": "admin",
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")
    r = client.post(
        "/admin/tenants",
        json={"name": "X", "slug": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


@pytest.mark.integration
def test_admin_jwt_valido_cria_tenant(client, admin_headers):
    r = client.post(
        "/admin/tenants",
        json={"name": "Empresa Auth", "slug": "empresa-auth"},
        headers=admin_headers,
    )
    assert r.status_code == 200
