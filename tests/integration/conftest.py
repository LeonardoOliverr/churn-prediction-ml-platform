"""
Fixtures compartilhadas pelos testes de integração.

Estratégia de isolamento: TRUNCATE antes de cada teste + commits reais.
Setup automático de banco com fingerprint MD5 para re-deploy só quando
os arquivos SQL de migração mudarem (padrão enterprise).
"""

import hashlib
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import bcrypt
import numpy as np
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text

# ─── Paths e constantes ───────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DB_DIR = _PROJECT_ROOT / "db"
_DB_DEPLOY_DIR = _DB_DIR / "deploy"

TEST_DATABASE_URL = "postgresql://churn_user:churn_pass@localhost:5434/churn_test"
_MAINTENANCE_URL = "postgresql://churn_user:churn_pass@localhost:5434/postgres"
TEST_SECRET_KEY = "test-secret-key-integration-tests-only"

# ─── Payload mínimo válido para POST /predict ─────────────────────────────────

MINIMAL_PAYLOAD = {
    "customer_id": "test-customer-001",
    "tenure_months": 12,
    "monthly_charges": 65.5,
    "total_charges": 786.0,
    "contract": "Month-to-month",
    "internet_service": "Fiber optic",
    "payment_method": "Electronic check",
    "gender": "Male",
    "senior_citizen": 0,
    "partner": 0,
    "dependents": 0,
    "phone_service": 1,
    "multiple_lines": "No",
    "online_security": "No",
    "online_backup": "No",
    "device_protection": "No",
    "tech_support": "No",
    "streaming_tv": "No",
    "streaming_movies": "No",
    "paperless_billing": 1,
}

_TRUNCATE_SQL = text("""
    TRUNCATE
        churn.evaluation_run_results,
        churn.evaluation_runs,
        churn.outcomes,
        churn.predictions,
        churn.project_model_config,
        churn.api_keys,
        churn.customers,
        churn.projects,
        churn.models,
        churn.tenants
    CASCADE
""")

# ─── Helpers de setup enterprise ─────────────────────────────────────────────


def _schema_fingerprint() -> str:
    """MD5 de todos os SQL de deploy em ordem — detecta qualquer mudança de schema."""
    sql_files = sorted(_DB_DEPLOY_DIR.glob("*.sql"))
    h = hashlib.md5()
    for f in sql_files:
        h.update(f.read_bytes())
    return h.hexdigest()


def _create_test_db_if_missing() -> None:
    """Cria churn_test se não existir. Usa AUTOCOMMIT pois CREATE DATABASE
    não pode rodar dentro de transação."""
    admin_engine = create_engine(_MAINTENANCE_URL, isolation_level="AUTOCOMMIT", echo=False)
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'churn_test'")
            ).fetchone()
            if not exists:
                conn.execute(text("CREATE DATABASE churn_test OWNER churn_user"))
                print("\n[setup-db] churn_test criado.")
            else:
                print("\n[setup-db] churn_test já existe.")
    finally:
        admin_engine.dispose()


def _get_stored_fingerprint(engine) -> str | None:
    """Lê fingerprint salvo em churn_test_meta.schema_info, retorna None se ausente."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT fingerprint FROM churn_test_meta.schema_info WHERE id = 1")
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _store_fingerprint(engine, fingerprint: str) -> None:
    """Persiste fingerprint após deploy bem-sucedido (upsert)."""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS churn_test_meta"))
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS churn_test_meta.schema_info (
                id            INT PRIMARY KEY,
                fingerprint   TEXT        NOT NULL,
                deployed_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text("""
                INSERT INTO churn_test_meta.schema_info (id, fingerprint)
                VALUES (1, :fp)
                ON CONFLICT (id) DO UPDATE
                    SET fingerprint = EXCLUDED.fingerprint,
                        deployed_at  = NOW()
            """),
            {"fp": fingerprint},
        )


def _run_sqitch_deploy() -> None:
    """Executa sqitch deploy incremental no banco churn_test via wrapper Docker.

    Sqitch rastreia o que já foi aplicado — idempotente por design.
    Migrations com CREATE ROLE (como a 19) não são re-executadas se já
    constam no schema sqitch.changes.
    """
    bash = shutil.which("bash")
    if bash is None:
        raise RuntimeError(
            "bash não encontrado no PATH. "
            "Instale Git for Windows, use WSL ou adicione bash ao PATH."
        )

    target = "db:pg://churn_user:churn_pass@localhost:5434/churn_test"
    env = {**os.environ, "PGDATABASE": "churn_test"}

    result = subprocess.run(
        [bash, "sqitch", "deploy", "--target", target],
        cwd=str(_DB_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"sqitch deploy falhou (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
    print(f"\n[setup-db] sqitch deploy concluído.\n{result.stdout.strip()}")


# ─── Fixtures de sessão — setup automático do banco ──────────────────────────


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Configura env vars do banco de teste e reseta singletons de Settings/Engine."""
    import src.config
    import src.dependencies

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    os.environ["APP_SECRET_KEY"] = TEST_SECRET_KEY
    os.environ["BCRYPT_ROUNDS"] = "4"
    os.environ["API_KEY_CACHE_TTL_SECONDS"] = "1"
    os.environ["MODEL_CACHE_TTL_SECONDS"] = "1"

    src.config._settings = None
    src.dependencies._engine = None

    yield

    src.config._settings = None
    src.dependencies._engine = None


@pytest.fixture(scope="session", autouse=True)
def ensure_test_db(setup_test_env):
    """Cria churn_test automaticamente se não existir. Roda uma vez por sessão."""
    _create_test_db_if_missing()


@pytest.fixture(scope="session", autouse=True)
def ensure_test_schema(ensure_test_db):
    """Garante schema atualizado via sqitch incremental.

    Compara fingerprint MD5 dos arquivos SQL:
    - fingerprint igual ao armazenado → pula sqitch (sem mudanças)
    - fingerprint diferente → sqitch deploy (apenas novas migrations)
    """
    schema_engine = create_engine(TEST_DATABASE_URL, echo=False)
    try:
        current_fp = _schema_fingerprint()
        stored_fp = _get_stored_fingerprint(schema_engine)

        if current_fp == stored_fp:
            print(f"\n[setup-db] Schema up-to-date (fp={current_fp[:8]}…). Pulando sqitch.")
        else:
            prefix_stored = stored_fp[:8] if stored_fp else "none"
            print(
                f"\n[setup-db] Schema desatualizado "
                f"(stored={prefix_stored}…, current={current_fp[:8]}…). "
                f"Executando sqitch deploy…"
            )
            _run_sqitch_deploy()
            _store_fingerprint(schema_engine, current_fp)
    finally:
        schema_engine.dispose()


@pytest.fixture(scope="session")
def engine(ensure_test_schema):
    """Engine SQLAlchemy para churn_test. Criado uma vez por sessão."""
    return create_engine(TEST_DATABASE_URL, echo=False)


# ─── Fixtures de isolamento por teste ────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_db(engine):
    """Trunca tabelas de negócio e limpa caches antes de cada teste."""
    import src.dependencies
    from src.services.model_resolver import _cache, _cache_lock

    src.dependencies._api_key_cache.clear()
    with _cache_lock:
        _cache.clear()

    with engine.begin() as conn:
        conn.execute(_TRUNCATE_SQL)


@pytest.fixture()
def db_conn(engine):
    """Conexão direta ao banco de teste para seeds e verificações."""
    with engine.connect() as conn:
        yield conn


@pytest.fixture()
def client(db_conn):
    """TestClient com get_db injetado via dependency_override."""
    from src.dependencies import get_db
    from src.main import app

    def override_get_db():
        yield db_conn

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers():
    """JWT Bearer válido para endpoints /admin/*."""
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "admin-teste",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ─── Fixtures de seed ─────────────────────────────────────────────────────────


@pytest.fixture()
def seed_tenant(db_conn):
    """Insere tenant de teste e retorna seu UUID."""
    tenant_id = str(uuid.uuid4())
    db_conn.execute(
        text(
            "INSERT INTO churn.tenants (id, name, slug) VALUES (:id, 'Tenant Teste', 'tenant-teste')"
        ),
        {"id": tenant_id},
    )
    db_conn.commit()
    return tenant_id


@pytest.fixture()
def seed_project(db_conn, seed_tenant):
    """Insere projeto vinculado ao seed_tenant e retorna seu UUID."""
    project_id = str(uuid.uuid4())
    db_conn.execute(
        text("""
            INSERT INTO churn.projects (id, tenant_id, name, slug)
            VALUES (:id, :tenant_id, 'Projeto Teste', 'projeto-teste')
        """),
        {"id": project_id, "tenant_id": seed_tenant},
    )
    db_conn.commit()
    return project_id


@pytest.fixture()
def seed_api_key(db_conn, seed_tenant, seed_project):
    """Cria API key com escopos predict + predictions:read.
    Retorna (secret_plain, tenant_id, project_id)."""
    secret = "churn_live_sk_testkey0000000000000000000"
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
            "tenant_id": seed_tenant,
            "project_id": seed_project,
            "key_hash": key_hash,
            "key_prefix": secret[:20],
        },
    )
    db_conn.commit()
    return secret, seed_tenant, seed_project


@pytest.fixture()
def seed_model(db_conn, seed_tenant, seed_project):
    """Insere modelo aprovado vinculado ao seed_tenant/seed_project e retorna seu UUID."""
    model_id = str(uuid.uuid4())
    db_conn.execute(
        text("""
            INSERT INTO churn.models
                (id, tenant_id, project_id, name, version, status, mlflow_run_id, trained_at)
            VALUES
                (:id, :tenant_id, :project_id, 'TestModel', 'v-test', 'approved',
                 'fake-run-id-test-000', NOW())
        """),
        {"id": model_id, "tenant_id": seed_tenant, "project_id": seed_project},
    )
    db_conn.commit()
    return model_id


@pytest.fixture()
def seed_champion(db_conn, seed_tenant, seed_project, seed_model):
    """Configura seed_model como champion ativo com pipeline mock.

    O mock ignora o input e retorna probabilidade fixa [[0.7, 0.3]]
    (prob_nao_churn=0.7, prob_churn=0.3) para qualquer batch size.
    """
    from src.services.model_resolver import invalidate_model_cache

    db_conn.execute(
        text("""
            INSERT INTO churn.project_model_config
                (tenant_id, project_id, model_id, threshold, role, is_active,
                 environment, traffic_split, configured_at, configured_by,
                 created_at, updated_at)
            VALUES
                (:tenant_id, :project_id, :model_id, 0.5, 'champion', TRUE,
                 'production', 0.0, NOW(), 'test-fixture', NOW(), NOW())
        """),
        {"tenant_id": seed_tenant, "project_id": seed_project, "model_id": seed_model},
    )
    db_conn.commit()
    invalidate_model_cache(seed_tenant, seed_project)

    mock_pipeline = MagicMock()
    mock_pipeline.predict_proba.side_effect = lambda X: np.full((len(X), 2), [0.7, 0.3])

    with patch("src.services.model_resolver.mlflow.sklearn.load_model", return_value=mock_pipeline):
        yield seed_model
