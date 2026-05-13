"""
Testes de integração — endpoints de administração.

Cobre:
- CRUD de tenant, projeto e API key
- Configuração de champion e challenger
- Promoção de challenger a champion
- Listagem de keys
"""

import pytest


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_criar_tenant(client, admin_headers):
    r = client.post(
        "/admin/tenants",
        json={"name": "Empresa X", "slug": "empresa-x"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "empresa-x"
    assert "id" in body


@pytest.mark.integration
def test_criar_tenant_slug_duplicado(client, admin_headers):
    client.post(
        "/admin/tenants",
        json={"name": "Primeira", "slug": "mesmo-slug"},
        headers=admin_headers,
    )
    r = client.post(
        "/admin/tenants",
        json={"name": "Segunda", "slug": "mesmo-slug"},
        headers=admin_headers,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "conflict"


# ---------------------------------------------------------------------------
# Projetos
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_criar_projeto(client, admin_headers, seed_tenant):
    r = client.post(
        "/admin/projects",
        json={"tenant_id": seed_tenant, "name": "Projeto Y", "slug": "projeto-y"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "projeto-y"
    assert body["tenant_id"] == seed_tenant


@pytest.mark.integration
def test_criar_projeto_slug_duplicado_no_tenant(client, admin_headers, seed_tenant):
    client.post(
        "/admin/projects",
        json={"tenant_id": seed_tenant, "name": "P1", "slug": "slug-dup"},
        headers=admin_headers,
    )
    r = client.post(
        "/admin/projects",
        json={"tenant_id": seed_tenant, "name": "P2", "slug": "slug-dup"},
        headers=admin_headers,
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_gerar_api_key_secret_retornado_uma_vez(client, admin_headers, seed_tenant, seed_project):
    r = client.post(
        "/admin/keys",
        json={"tenant_id": seed_tenant, "project_id": seed_project, "scopes": ["predict"]},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "secret" in body
    assert body["secret"].startswith("churn_live_sk_")
    assert "id" in body
    assert body["tenant_id"] == seed_tenant


@pytest.mark.integration
def test_revogar_api_key(client, admin_headers, seed_tenant, seed_project):
    r = client.post(
        "/admin/keys",
        json={"tenant_id": seed_tenant, "project_id": seed_project, "scopes": ["predict"]},
        headers=admin_headers,
    )
    key_id = r.json()["id"]

    r2 = client.delete(f"/admin/keys/{key_id}", headers=admin_headers)
    assert r2.status_code == 200
    assert r2.json()["revoked"] == key_id


@pytest.mark.integration
def test_revogar_key_inexistente_retorna_404(client, admin_headers):
    import uuid

    r = client.delete(f"/admin/keys/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


@pytest.mark.integration
def test_listar_keys_do_tenant(client, admin_headers, seed_api_key):
    _, tenant_id, _ = seed_api_key
    r = client.get(f"/admin/tenants/{tenant_id}/keys", headers=admin_headers)
    assert r.status_code == 200
    keys = r.json()
    assert len(keys) >= 1
    # secret nunca é retornado em listagem
    for key in keys:
        assert "secret" not in key


# ---------------------------------------------------------------------------
# Champion / Challenger
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_configurar_champion(client, admin_headers, seed_tenant, seed_project, seed_model):
    r = client.post(
        f"/admin/tenants/{seed_tenant}/models/champion",
        params={"project_id": seed_project},
        json={"model_id": seed_model, "threshold": 0.45},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["config"]["role"] == "champion"
    assert body["config"]["model_id"] == seed_model
    assert abs(body["config"]["threshold"] - 0.45) < 0.001


@pytest.mark.integration
def test_configurar_champion_modelo_inexistente_retorna_409(client, admin_headers, seed_tenant, seed_project):
    import uuid

    r = client.post(
        f"/admin/tenants/{seed_tenant}/models/champion",
        params={"project_id": seed_project},
        json={"model_id": str(uuid.uuid4()), "threshold": 0.5},
        headers=admin_headers,
    )
    # Modelo não existe no catálogo → ModelNotFoundError → 404
    assert r.status_code == 404


@pytest.mark.integration
def test_promover_challenger_a_champion(
    client, admin_headers, seed_tenant, seed_project, seed_champion, db_conn
):
    """
    Configura um segundo modelo como challenger e o promove a champion.
    Verifica que o antigo champion foi desativado.
    """
    from sqlalchemy import text

    # Cria segundo modelo aprovado para o challenger
    import uuid

    model2_id = str(uuid.uuid4())
    db_conn.execute(
        text("""
            INSERT INTO churn.models
                (id, name, version, scope, status, mlflow_run_id, trained_at)
            VALUES
                (:id, 'ChallengerModel', 'v-chall', 'global', 'approved',
                 'fake-run-chall-000', NOW())
        """),
        {"id": model2_id},
    )
    db_conn.commit()

    # Configura como challenger
    r = client.post(
        f"/admin/tenants/{seed_tenant}/models/challenger",
        params={"project_id": seed_project},
        json={"model_id": model2_id, "threshold": 0.5, "traffic_split": 0.2},
        headers=admin_headers,
    )
    assert r.status_code == 200

    # Promove challenger a champion
    r2 = client.post(
        f"/admin/tenants/{seed_tenant}/models/{model2_id}/promote",
        params={"project_id": seed_project},
        json={},
        headers=admin_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["config"]["role"] == "champion"
    assert r2.json()["config"]["model_id"] == model2_id

    # Verifica que apenas um champion ativo existe no projeto
    r3 = client.get(
        f"/admin/tenants/{seed_tenant}/models/config",
        params={"project_id": seed_project},
        headers=admin_headers,
    )
    body = r3.json()
    assert body["champion"]["model_id"] == model2_id
    assert body["challenger"] is None
