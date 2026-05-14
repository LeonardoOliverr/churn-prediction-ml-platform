"""
Testes unitários para scripts/seed_outcomes_from_customers.py.

Cobre a lógica de seed sem dependência de banco de dados:
- seed_outcomes() com dry_run=True: não executa writes
- seed_outcomes() sem resultados: retorna 0 sem tentar inserir
- seed_outcomes() com linhas: executa INSERT para cada linha
- Idempotência via ON CONFLICT DO NOTHING
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _make_fake_row(i: int):
    """Cria uma linha fake simulando o resultado da query de candidatos."""
    return SimpleNamespace(
        prediction_id=f"pred-uuid-{i}",
        tenant_id="tenant-uuid",
        project_id="project-uuid",
        customer_id=f"CUST-{i:04d}",
        requested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        churn_value=i % 2,
    )


def _make_mock_engine(rows: list):
    """Monta um engine mockado que retorna as linhas informadas na query."""
    mock_conn_read = MagicMock()
    mock_conn_read.__enter__ = lambda s: s
    mock_conn_read.__exit__ = MagicMock(return_value=False)
    mock_conn_read.execute.return_value.fetchall.return_value = rows
    mock_conn_read.execute.return_value.scalar_one.return_value = "uuid"

    mock_conn_write = MagicMock()
    mock_conn_write.__enter__ = lambda s: s
    mock_conn_write.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn_read
    mock_engine.begin.return_value = mock_conn_write

    return mock_engine, mock_conn_write


# ---------------------------------------------------------------------------
# dry_run=True — nenhuma escrita
# ---------------------------------------------------------------------------


def test_seed_outcomes_dry_run_returns_candidate_count():
    """dry_run=True retorna o número de candidatos sem inserir."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    rows = [_make_fake_row(i) for i in range(5)]
    mock_engine, mock_conn_write = _make_mock_engine(rows)

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        count = seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=True)

    assert count == 5


def test_seed_outcomes_dry_run_does_not_write():
    """dry_run=True não executa nenhum INSERT."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    rows = [_make_fake_row(i) for i in range(3)]
    mock_engine, mock_conn_write = _make_mock_engine(rows)

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=True)

    mock_conn_write.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Sem candidatos
# ---------------------------------------------------------------------------


def test_seed_outcomes_no_rows_returns_zero():
    """Sem predições holdout sem outcome, retorna 0."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    mock_engine, mock_conn_write = _make_mock_engine(rows=[])

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        count = seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=False)

    assert count == 0


def test_seed_outcomes_no_rows_does_not_write():
    """Sem candidatos, nenhum INSERT é executado."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    mock_engine, mock_conn_write = _make_mock_engine(rows=[])

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=False)

    mock_conn_write.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Escrita real
# ---------------------------------------------------------------------------


def test_seed_outcomes_inserts_one_per_row():
    """Um INSERT é executado para cada linha candidata."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    rows = [_make_fake_row(i) for i in range(4)]
    mock_engine, mock_conn_write = _make_mock_engine(rows)

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        count = seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=False)

    assert count == 4
    assert mock_conn_write.execute.call_count == 4


def test_seed_outcomes_maps_churn_value_to_churned():
    """churn_value=1 é mapeado para churned=True; churn_value=0 para churned=False."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    rows = [
        _make_fake_row(0),  # churn_value=0 → churned=False
        _make_fake_row(1),  # churn_value=1 → churned=True
    ]
    mock_engine, mock_conn_write = _make_mock_engine(rows)

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=False)

    calls = mock_conn_write.execute.call_args_list
    params_0 = calls[0][0][1]
    params_1 = calls[1][0][1]
    assert params_0["churned"] is False
    assert params_1["churned"] is True


def test_seed_outcomes_confirmed_at_equals_requested_at():
    """confirmed_at é igual a requested_at (natureza simulada do holdout)."""
    from scripts.seed_outcomes_from_customers import seed_outcomes

    ts = datetime(2026, 3, 15, tzinfo=timezone.utc)
    row = _make_fake_row(0)
    row.requested_at = ts

    mock_engine, mock_conn_write = _make_mock_engine([row])

    with (
        patch("scripts.seed_outcomes_from_customers._build_engine", return_value=mock_engine),
        patch("scripts.seed_outcomes_from_customers._resolve_tenant_id", return_value="t"),
        patch("scripts.seed_outcomes_from_customers._resolve_project_id", return_value="p"),
    ):
        seed_outcomes("ibm-telco", "telco-churn-2018", dry_run=False)

    params = mock_conn_write.execute.call_args_list[0][0][1]
    assert params["confirmed_at"] == ts
