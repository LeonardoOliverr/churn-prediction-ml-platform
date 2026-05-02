"""
Testes unitários para ml/baseline.py.

Inclui:
- [SMOKE TEST] Pipeline mínimo: preprocess → fit → predict sem DB ou MLflow
- Testes da interface sklearn dos modelos configurados
- Testes das funções puras: _derive_scope() e _cv_metrics()
"""

import argparse
import sys

import numpy as np
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from unittest.mock import MagicMock, call, patch

from ml.config import TARGET
from ml.preprocessing import build_preprocessor


# Métricas fake reutilizadas em vários testes
_FAKE_METRICS = {
    "f1_mean": 0.65, "f1_std": 0.04,
    "roc_auc_mean": 0.85, "roc_auc_std": 0.02,
    "recall_mean": 0.80, "recall_std": 0.04,
    "precision_mean": 0.70, "precision_std": 0.03,
}
_DUMMY_METRICS = {k: 0.25 for k in _FAKE_METRICS}


# ---------------------------------------------------------------------------
# SMOKE TEST — fluxo mínimo end-to-end sem dependências externas
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_smoke_pipeline(fake_customers_df):
    """[SMOKE TEST] Fluxo mínimo load → preprocess → train → predict não quebra.

    Valida que DummyClassifier consegue fit + predict + predict_proba
    usando o preprocessor real e dados fake, sem banco nem MLflow.
    """
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", DummyClassifier(strategy="stratified", random_state=42)),
        ]
    )

    pipeline.fit(X, y)
    predictions = pipeline.predict(X)
    probabilities = pipeline.predict_proba(X)

    assert len(predictions) == len(fake_customers_df)
    assert probabilities.shape == (len(fake_customers_df), 2)
    assert set(predictions).issubset({0, 1})


@pytest.mark.smoke
def test_smoke_pipeline_logistic_regression(fake_customers_df):
    """[SMOKE TEST] LogisticRegression treina e prediz sem erros com dados fake."""
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )

    pipeline.fit(X, y)
    predictions = pipeline.predict(X)
    probabilities = pipeline.predict_proba(X)

    assert len(predictions) == len(fake_customers_df)
    assert probabilities.shape[1] == 2
    assert all(0.0 <= p <= 1.0 for p in probabilities[:, 1])


# ---------------------------------------------------------------------------
# Interface sklearn dos modelos configurados
# ---------------------------------------------------------------------------


def test_models_have_fit_method():
    """Todos os modelos em MODELS possuem método fit."""
    from ml.baseline import MODELS

    for name, model in MODELS.items():
        assert hasattr(model, "fit"), f"Modelo '{name}' não tem método fit."


def test_models_have_predict_method():
    """Todos os modelos em MODELS possuem método predict."""
    from ml.baseline import MODELS

    for name, model in MODELS.items():
        assert hasattr(model, "predict"), f"Modelo '{name}' não tem método predict."


def test_models_have_predict_proba_method():
    """Todos os modelos em MODELS possuem método predict_proba."""
    from ml.baseline import MODELS

    for name, model in MODELS.items():
        assert hasattr(model, "predict_proba"), (
            f"Modelo '{name}' não tem método predict_proba."
        )


def test_models_dict_contains_expected_keys():
    """MODELS contém DummyClassifier e LogisticRegression."""
    from ml.baseline import MODELS

    assert "dummy_stratified" in MODELS
    assert "logistic_regression" in MODELS


# ---------------------------------------------------------------------------
# _derive_scope() — função pura, sem dependências externas
# ---------------------------------------------------------------------------


def test_derive_scope_global():
    """(None, None) → escopo global."""
    from ml.baseline import _derive_scope

    scope, experiment, model_name = _derive_scope(None, None)
    assert scope == "global"
    assert "global" in experiment
    assert "global" in model_name


def test_derive_scope_tenant():
    """(slug, None) → escopo tenant."""
    from ml.baseline import _derive_scope

    scope, experiment, model_name = _derive_scope("ibm-telco", None)
    assert scope == "tenant"
    assert "ibm-telco" in experiment


def test_derive_scope_project():
    """(slug, slug) → escopo project."""
    from ml.baseline import _derive_scope

    scope, experiment, model_name = _derive_scope("ibm-telco", "telco-churn-2018")
    assert scope == "project"
    assert "ibm-telco" in experiment
    assert "telco-churn-2018" in experiment


def test_derive_scope_project_requires_tenant():
    """Escopos retornados são sempre um dos três valores válidos."""
    from ml.baseline import _derive_scope

    for args, expected_scope in [
        ((None, None), "global"),
        (("slug", None), "tenant"),
        (("slug", "proj"), "project"),
    ]:
        scope, _, _ = _derive_scope(*args)
        assert scope == expected_scope


# ---------------------------------------------------------------------------
# _cv_metrics() — com mock de cross_validate para evitar 5-fold com dados fake
# ---------------------------------------------------------------------------


def test_cv_metrics_returns_expected_keys(fake_customers_df):
    """_cv_metrics() retorna todas as chaves de métricas esperadas."""
    from ml.baseline import _cv_metrics, SCORING

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", DummyClassifier(strategy="stratified", random_state=42)),
        ]
    )

    fake_cv_results = {
        f"test_{metric}": np.array([0.5, 0.6, 0.55, 0.58, 0.52])
        for metric in SCORING
    }

    with patch("ml.baseline.cross_validate", return_value=fake_cv_results):
        metrics = _cv_metrics(pipeline, X, y)

    expected_keys = [f"{m}_{stat}" for m in SCORING for stat in ("mean", "std")]
    for key in expected_keys:
        assert key in metrics, f"Chave ausente em metrics: '{key}'"


def test_cv_metrics_values_are_floats(fake_customers_df):
    """Todos os valores retornados por _cv_metrics() são float."""
    from ml.baseline import _cv_metrics, SCORING

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", DummyClassifier(strategy="stratified", random_state=42)),
        ]
    )

    fake_cv_results = {
        f"test_{metric}": np.array([0.5, 0.6, 0.55, 0.58, 0.52])
        for metric in SCORING
    }

    with patch("ml.baseline.cross_validate", return_value=fake_cv_results):
        metrics = _cv_metrics(pipeline, X, y)

    for key, value in metrics.items():
        assert isinstance(value, float), f"'{key}' deveria ser float, got {type(value)}"


# ---------------------------------------------------------------------------
# _parse_args() — parsing de argumentos CLI
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    """Sem argumentos → tenant=None, project=None, dry_run=False."""
    from ml.baseline import _parse_args

    with patch.object(sys, "argv", ["baseline.py"]):
        args = _parse_args()

    assert args.tenant is None
    assert args.project is None
    assert args.dry_run is False


def test_parse_args_tenant_only():
    """--tenant define tenant sem afetar project ou dry_run."""
    from ml.baseline import _parse_args

    with patch.object(sys, "argv", ["baseline.py", "--tenant", "ibm-telco"]):
        args = _parse_args()

    assert args.tenant == "ibm-telco"
    assert args.project is None
    assert args.dry_run is False


def test_parse_args_tenant_and_project():
    """--tenant + --project definem ambos os escopos."""
    from ml.baseline import _parse_args

    with patch.object(sys, "argv", ["baseline.py", "--tenant", "ibm-telco", "--project", "telco-churn-2018"]):
        args = _parse_args()

    assert args.tenant == "ibm-telco"
    assert args.project == "telco-churn-2018"


def test_parse_args_dry_run_flag():
    """--dry-run ativa o modo de simulação."""
    from ml.baseline import _parse_args

    with patch.object(sys, "argv", ["baseline.py", "--dry-run"]):
        args = _parse_args()

    assert args.dry_run is True


def test_parse_args_project_without_tenant_exits():
    """--project sem --tenant deve encerrar com SystemExit."""
    from ml.baseline import _parse_args

    with patch.object(sys, "argv", ["baseline.py", "--project", "telco-churn-2018"]):
        with pytest.raises(SystemExit):
            _parse_args()


# ---------------------------------------------------------------------------
# _run_model() — treinamento, métricas e logging MLflow
# ---------------------------------------------------------------------------


def test_run_model_dry_run_returns_sentinel_id(fake_customers_df):
    """dry_run=True retorna 'dry-run-run-id' sem abrir run no MLflow."""
    from ml.baseline import _run_model

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    model = DummyClassifier(strategy="stratified", random_state=42)

    with patch("ml.baseline._cv_metrics", return_value=_FAKE_METRICS):
        run_id, metrics = _run_model("dummy_stratified", model, X, y, dry_run=True)

    assert run_id == "dry-run-run-id"
    assert metrics == _FAKE_METRICS


def test_run_model_dry_run_does_not_call_mlflow(fake_customers_df):
    """dry_run=True não deve chamar mlflow.start_run."""
    from ml.baseline import _run_model

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    model = DummyClassifier(strategy="stratified", random_state=42)

    with patch("ml.baseline._cv_metrics", return_value=_FAKE_METRICS), \
         patch("ml.baseline.mlflow.start_run") as mock_start_run:
        _run_model("dummy_stratified", model, X, y, dry_run=True)

    mock_start_run.assert_not_called()


def test_run_model_not_dry_run_returns_mlflow_run_id(fake_customers_df):
    """dry_run=False retorna o run_id do MLflow e registra métricas, params e artefato."""
    from ml.baseline import _run_model

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    model = DummyClassifier(strategy="stratified", random_state=42)

    mock_run = MagicMock()
    mock_run.info.run_id = "mlflow-abc-123"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_run)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("ml.baseline._cv_metrics", return_value=_FAKE_METRICS), \
         patch("ml.baseline.mlflow.start_run", return_value=mock_ctx), \
         patch("ml.baseline.mlflow.log_params") as mock_log_params, \
         patch("ml.baseline.mlflow.log_metrics") as mock_log_metrics, \
         patch("ml.baseline.mlflow.sklearn.log_model") as mock_log_model:
        run_id, metrics = _run_model("dummy_stratified", model, X, y, dry_run=False)

    assert run_id == "mlflow-abc-123"
    assert metrics == _FAKE_METRICS
    mock_log_params.assert_called_once()
    mock_log_metrics.assert_called_once_with(_FAKE_METRICS)
    mock_log_model.assert_called_once()
    assert mock_log_model.call_args.kwargs["artifact_path"] == "model"


# ---------------------------------------------------------------------------
# _next_version() — cálculo de versão semântica baseado em contagem no DB
# ---------------------------------------------------------------------------


def _make_mock_conn(count: int) -> MagicMock:
    """Cria um mock de conexão SQLAlchemy que retorna `count` para scalar()."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.scalar.return_value = count
    return mock_conn


def test_next_version_first_model_is_v1():
    """Quando não existe nenhum modelo registrado, retorna 'v1'."""
    from ml.baseline import _next_version

    conn = _make_mock_conn(count=0)
    version = _next_version(conn, "global", None, None, "global-baseline")
    assert version == "v1"


def test_next_version_increments_correctly():
    """Quando já existem 3 versões, retorna 'v4'."""
    from ml.baseline import _next_version

    conn = _make_mock_conn(count=3)
    version = _next_version(conn, "global", None, None, "global-baseline")
    assert version == "v4"


def test_next_version_passes_correct_params_to_query():
    """Os parâmetros de escopo são passados corretamente à query."""
    from ml.baseline import _next_version

    conn = _make_mock_conn(count=0)
    _next_version(conn, "tenant", "tenant-uuid", None, "my-model")

    call_kwargs = conn.execute.call_args[0][1]
    assert call_kwargs["scope"] == "tenant"
    assert call_kwargs["tenant_id"] == "tenant-uuid"
    assert call_kwargs["name"] == "my-model"


# ---------------------------------------------------------------------------
# _register_in_db() — registro de modelos no banco com suporte a dry-run
# ---------------------------------------------------------------------------


def _make_mock_engine() -> tuple[MagicMock, MagicMock]:
    """Retorna (mock_engine, mock_conn) configurados como context manager."""
    mock_conn = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx
    return mock_engine, mock_conn


def test_register_in_db_dry_run_no_db_writes(capsys):
    """dry_run=True imprime o registro e não executa nenhuma query de escrita."""
    from ml.baseline import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v1"):
        _register_in_db(
            name="global-baseline",
            run_id="test-run-id",
            metrics=_FAKE_METRICS,
            scope="global",
            tenant_slug=None,
            project_slug=None,
            status="active",
            dry_run=True,
        )

    captured = capsys.readouterr()
    assert "dry-run" in captured.out
    assert "Nenhuma escrita realizada" in captured.out
    mock_conn.execute.assert_not_called()


def test_register_in_db_active_status_executes_update_and_insert():
    """status='active' executa UPDATE de arquivamento + INSERT do novo modelo."""
    from ml.baseline import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v2"):
        _register_in_db(
            name="global-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="global",
            tenant_slug=None,
            project_slug=None,
            status="active",
            dry_run=False,
        )

    # UPDATE (archive anterior) + INSERT (novo modelo)
    assert mock_conn.execute.call_count == 2


def test_register_in_db_shadow_status_executes_only_insert():
    """status='shadow' executa apenas INSERT, sem UPDATE de arquivamento."""
    from ml.baseline import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v1"):
        _register_in_db(
            name="global-baseline",
            run_id="run-id",
            metrics=_DUMMY_METRICS,
            scope="global",
            tenant_slug=None,
            project_slug=None,
            status="shadow",
            dry_run=False,
        )

    # Apenas INSERT, sem UPDATE
    assert mock_conn.execute.call_count == 1


def test_register_in_db_dry_run_includes_version_in_output(capsys):
    """O output do dry-run inclui a versão calculada."""
    from ml.baseline import _register_in_db

    mock_engine, _ = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v3"):
        _register_in_db(
            name="global-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="global",
            tenant_slug=None,
            project_slug=None,
            status="active",
            dry_run=True,
        )

    assert "v3" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _register_in_db() — scopes tenant e project
# ---------------------------------------------------------------------------


def test_register_in_db_tenant_scope_calls_resolve_tenant_id():
    """Escopo tenant chama _resolve_tenant_id e não chama _resolve_project_id."""
    from ml.baseline import _register_in_db

    mock_engine, _ = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v1"), \
         patch("ml.baseline._resolve_tenant_id", return_value="tenant-uuid") as mock_tid, \
         patch("ml.baseline._resolve_project_id") as mock_pid:
        _register_in_db(
            name="ibm-telco-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="tenant",
            tenant_slug="ibm-telco",
            project_slug=None,
            status="active",
            dry_run=True,
        )

    mock_tid.assert_called()
    mock_pid.assert_not_called()


def test_register_in_db_project_scope_calls_both_resolvers():
    """Escopo project chama _resolve_tenant_id e _resolve_project_id."""
    from ml.baseline import _register_in_db

    mock_engine, _ = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v1"), \
         patch("ml.baseline._resolve_tenant_id", return_value="tenant-uuid") as mock_tid, \
         patch("ml.baseline._resolve_project_id", return_value="project-uuid") as mock_pid:
        _register_in_db(
            name="ibm-telco-telco-churn-2018-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="project",
            tenant_slug="ibm-telco",
            project_slug="telco-churn-2018",
            status="active",
            dry_run=True,
        )

    mock_tid.assert_called()
    mock_pid.assert_called()


def test_register_in_db_tenant_scope_not_dry_run_executes_writes():
    """Escopo tenant, dry_run=False executa UPDATE + INSERT sem erros."""
    from ml.baseline import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v1"), \
         patch("ml.baseline._resolve_tenant_id", return_value="tenant-uuid"), \
         patch("ml.baseline._resolve_project_id", return_value=None):
        _register_in_db(
            name="ibm-telco-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="tenant",
            tenant_slug="ibm-telco",
            project_slug=None,
            status="active",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 2


def test_register_in_db_project_scope_not_dry_run_shadow_executes_only_insert():
    """Escopo project, dry_run=False, status='shadow' executa apenas INSERT."""
    from ml.baseline import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.baseline._build_engine", return_value=mock_engine), \
         patch("ml.baseline._next_version", return_value="v1"), \
         patch("ml.baseline._resolve_tenant_id", return_value="tenant-uuid"), \
         patch("ml.baseline._resolve_project_id", return_value="project-uuid"):
        _register_in_db(
            name="ibm-telco-telco-churn-2018-baseline",
            run_id="run-id",
            metrics=_DUMMY_METRICS,
            scope="project",
            tenant_slug="ibm-telco",
            project_slug="telco-churn-2018",
            status="shadow",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 1


# ---------------------------------------------------------------------------
# main() — orquestração completa do pipeline de treinamento
# ---------------------------------------------------------------------------


def _fake_run_model_side_effect(name, model, X, y, dry_run):
    """Retorna métricas diferentes por modelo para simular comparação realista."""
    if name == "logistic_regression":
        return ("run-lr", _FAKE_METRICS)
    return ("run-dummy", _DUMMY_METRICS)


def test_main_dry_run_calls_run_model_for_each_model(fake_customers_df):
    """main() com dry_run=True chama _run_model e _register_in_db para cada modelo em MODELS."""
    from ml.baseline import main, MODELS

    fake_args = argparse.Namespace(tenant=None, project=None, dry_run=True)
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.baseline._parse_args", return_value=fake_args), \
         patch("ml.baseline.load_data", return_value=(X, y)), \
         patch("ml.baseline._run_model", side_effect=_fake_run_model_side_effect) as mock_run, \
         patch("ml.baseline._register_in_db") as mock_register:
        main()

    assert mock_run.call_count == len(MODELS)
    assert mock_register.call_count == len(MODELS)


def test_main_dry_run_does_not_configure_mlflow(fake_customers_df):
    """main() com dry_run=True não chama mlflow.set_tracking_uri nem set_experiment."""
    from ml.baseline import main

    fake_args = argparse.Namespace(tenant=None, project=None, dry_run=True)
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.baseline._parse_args", return_value=fake_args), \
         patch("ml.baseline.load_data", return_value=(X, y)), \
         patch("ml.baseline._run_model", side_effect=_fake_run_model_side_effect), \
         patch("ml.baseline._register_in_db"), \
         patch("ml.baseline.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.baseline.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_not_called()
    mock_exp.assert_not_called()


def test_main_not_dry_run_marks_best_model_as_active(fake_customers_df):
    """main() sem dry_run marca logistic_regression (maior f1) como 'active' e dummy como 'shadow'."""
    from ml.baseline import main

    fake_args = argparse.Namespace(tenant=None, project=None, dry_run=False)
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.baseline._parse_args", return_value=fake_args), \
         patch("ml.baseline.load_data", return_value=(X, y)), \
         patch("ml.baseline._run_model", side_effect=_fake_run_model_side_effect), \
         patch("ml.baseline._register_in_db") as mock_register, \
         patch("ml.baseline.mlflow.set_tracking_uri"), \
         patch("ml.baseline.mlflow.set_experiment"):
        main()

    statuses = {c.kwargs["name"]: c.kwargs["status"] for c in mock_register.call_args_list}
    assert statuses["logistic_regression"] == "active"
    assert statuses["dummy_stratified"] == "shadow"


def test_main_not_dry_run_configures_mlflow(fake_customers_df):
    """main() sem dry_run chama mlflow.set_tracking_uri e set_experiment."""
    from ml.baseline import main

    fake_args = argparse.Namespace(tenant="ibm-telco", project=None, dry_run=False)
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.baseline._parse_args", return_value=fake_args), \
         patch("ml.baseline.load_data", return_value=(X, y)), \
         patch("ml.baseline._run_model", side_effect=_fake_run_model_side_effect), \
         patch("ml.baseline._register_in_db"), \
         patch("ml.baseline.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.baseline.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_called_once()
    mock_exp.assert_called_once_with("ibm-telco/baseline")
