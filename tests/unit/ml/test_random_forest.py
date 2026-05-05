"""
Testes unitários para ml/models/random_forest/random_forest.py.

Inclui:
- [SMOKE TEST] Pipeline mínimo: preprocess → fit → predict sem DB ou MLflow
- Testes da interface sklearn do RandomForestClassifier
- Testes das funções puras: _derive_scope(), _model_name(), _cv_metrics()
- Testes de _run_model() com dry-run e mock de MLflow (inclui feature_importances)
- Testes de _register_in_db() com dry-run e mock de DB
- Testes de main() — orquestração completa com mocks
"""

import argparse
import sys

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from unittest.mock import MagicMock, patch

from ml.core.config import TARGET
from ml.core.preprocessing import build_preprocessor


_FAKE_METRICS = {
    "f1_mean": 0.71, "f1_std": 0.03,
    "roc_auc_mean": 0.90, "roc_auc_std": 0.01,
    "recall_mean": 0.83, "recall_std": 0.03,
    "precision_mean": 0.63, "precision_std": 0.04,
    "train_f1_mean": 0.98,
    "train_roc_auc_mean": 0.99,
    "train_recall_mean": 0.97,
    "train_precision_mean": 0.98,
}


# ---------------------------------------------------------------------------
# SMOKE TEST — fluxo mínimo end-to-end sem dependências externas
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_smoke_pipeline_random_forest(fake_customers_df):
    """[SMOKE TEST] RandomForestClassifier treina e prediz sem erros com dados fake."""
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(
                n_estimators=10,
                random_state=42,
                class_weight="balanced",
            )),
        ]
    )

    pipeline.fit(X, y)
    predictions = pipeline.predict(X)
    probabilities = pipeline.predict_proba(X)

    assert len(predictions) == len(fake_customers_df)
    assert probabilities.shape == (len(fake_customers_df), 2)
    assert set(predictions).issubset({0, 1})
    assert all(0.0 <= p <= 1.0 for p in probabilities[:, 1])


# ---------------------------------------------------------------------------
# Interface sklearn do RandomForestClassifier
# ---------------------------------------------------------------------------


def test_random_forest_has_fit_method():
    """RandomForestClassifier possui método fit."""
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    assert hasattr(model, "fit")


def test_random_forest_has_predict_method():
    """RandomForestClassifier possui método predict."""
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    assert hasattr(model, "predict")


def test_random_forest_has_predict_proba_method():
    """RandomForestClassifier possui método predict_proba."""
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    assert hasattr(model, "predict_proba")


def test_random_forest_has_feature_importances_after_fit(fake_customers_df):
    """Após fit, feature_importances_ está disponível e soma 1.0."""
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(
                n_estimators=10, random_state=42, class_weight="balanced"
            )),
        ]
    )
    pipeline.fit(X, y)

    importances = pipeline.named_steps["classifier"].feature_importances_
    assert importances is not None
    assert abs(importances.sum() - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# _derive_scope() — retorna 2-tuple (scope, experiment_name)
# ---------------------------------------------------------------------------


def test_derive_scope_global():
    """(None, None) → escopo global, experimento global/random-forest."""
    from ml.models.random_forest.random_forest import _derive_scope

    scope, experiment = _derive_scope(None, None)
    assert scope == "global"
    assert experiment == "global/random-forest"


def test_derive_scope_tenant():
    """(slug, None) → escopo tenant, experimento contém o slug."""
    from ml.models.random_forest.random_forest import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", None)
    assert scope == "tenant"
    assert "ibm-telco" in experiment
    assert "random-forest" in experiment


def test_derive_scope_project():
    """(slug, slug) → escopo project, experimento contém tenant e projeto."""
    from ml.models.random_forest.random_forest import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", "telco-churn-2018")
    assert scope == "project"
    assert "ibm-telco" in experiment
    assert "telco-churn-2018" in experiment


def test_derive_scope_returns_two_tuple():
    """_derive_scope retorna sempre uma tupla de 2 elementos."""
    from ml.models.random_forest.random_forest import _derive_scope

    for args in [(None, None), ("t", None), ("t", "p")]:
        result = _derive_scope(*args)
        assert len(result) == 2, f"Esperado 2-tuple, got {len(result)}-tuple para {args}"


# ---------------------------------------------------------------------------
# _model_name() — gera o nome do modelo para registro em churn.models
# ---------------------------------------------------------------------------


def test_model_name_global():
    """Escopo global → 'global-random-forest'."""
    from ml.models.random_forest.random_forest import _model_name

    assert _model_name("global", None, None) == "global-random-forest"


def test_model_name_tenant():
    """Escopo tenant → '{tenant}-random-forest'."""
    from ml.models.random_forest.random_forest import _model_name

    assert _model_name("tenant", "ibm-telco", None) == "ibm-telco-random-forest"


def test_model_name_project():
    """Escopo project → '{tenant}-{project}-random-forest'."""
    from ml.models.random_forest.random_forest import _model_name

    name = _model_name("project", "ibm-telco", "telco-churn-2018")
    assert name == "ibm-telco-telco-churn-2018-random-forest"


# ---------------------------------------------------------------------------
# _cv_metrics() — com mock de cross_validate para evitar 5-fold com dados fake
# ---------------------------------------------------------------------------


def test_cv_metrics_returns_expected_keys(fake_customers_df):
    """_cv_metrics() retorna todas as chaves de métricas esperadas."""
    from ml.models.random_forest.random_forest import _cv_metrics, SCORING

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(
                n_estimators=10, random_state=42, class_weight="balanced"
            )),
        ]
    )

    fake_cv_results = {
        **{f"test_{metric}":  np.array([0.5, 0.6, 0.55, 0.58, 0.52]) for metric in SCORING},
        **{f"train_{metric}": np.array([0.9, 0.91, 0.89, 0.90, 0.88]) for metric in SCORING},
    }

    with patch("ml.models.random_forest.random_forest.cross_validate", return_value=fake_cv_results):
        metrics = _cv_metrics(pipeline, X, y)

    expected_keys = (
        [f"{m}_{stat}" for m in SCORING for stat in ("mean", "std")]
        + [f"train_{m}_mean" for m in SCORING]
    )
    for key in expected_keys:
        assert key in metrics, f"Chave ausente em metrics: '{key}'"


def test_cv_metrics_values_are_floats(fake_customers_df):
    """Todos os valores retornados por _cv_metrics() são float."""
    from ml.models.random_forest.random_forest import _cv_metrics, SCORING

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(
                n_estimators=10, random_state=42, class_weight="balanced"
            )),
        ]
    )

    fake_cv_results = {
        **{f"test_{metric}":  np.array([0.5, 0.6, 0.55, 0.58, 0.52]) for metric in SCORING},
        **{f"train_{metric}": np.array([0.9, 0.91, 0.89, 0.90, 0.88]) for metric in SCORING},
    }

    with patch("ml.models.random_forest.random_forest.cross_validate", return_value=fake_cv_results):
        metrics = _cv_metrics(pipeline, X, y)

    for key, value in metrics.items():
        assert isinstance(value, float), f"'{key}' deveria ser float, got {type(value)}"


# ---------------------------------------------------------------------------
# _parse_args() — parsing de argumentos CLI
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    """Sem argumentos → tenant=None, project=None, dry_run=False, n_estimators=500, max_depth=None."""
    from ml.models.random_forest.random_forest import _parse_args

    with patch.object(sys, "argv", ["random_forest.py"]):
        args = _parse_args()

    assert args.tenant is None
    assert args.project is None
    assert args.dry_run is False
    assert args.n_estimators == 500
    assert args.max_depth is None


def test_parse_args_n_estimators():
    """--n-estimators sobrescreve o default de 500."""
    from ml.models.random_forest.random_forest import _parse_args

    with patch.object(sys, "argv", ["random_forest.py", "--n-estimators", "300"]):
        args = _parse_args()

    assert args.n_estimators == 300


def test_parse_args_max_depth():
    """--max-depth define a profundidade máxima."""
    from ml.models.random_forest.random_forest import _parse_args

    with patch.object(sys, "argv", ["random_forest.py", "--max-depth", "10"]):
        args = _parse_args()

    assert args.max_depth == 10


def test_parse_args_dry_run_flag():
    """--dry-run ativa o modo de simulação."""
    from ml.models.random_forest.random_forest import _parse_args

    with patch.object(sys, "argv", ["random_forest.py", "--dry-run"]):
        args = _parse_args()

    assert args.dry_run is True


def test_parse_args_project_without_tenant_exits():
    """--project sem --tenant deve encerrar com SystemExit."""
    from ml.models.random_forest.random_forest import _parse_args

    with patch.object(sys, "argv", ["random_forest.py", "--project", "telco-churn-2018"]):
        with pytest.raises(SystemExit):
            _parse_args()


# ---------------------------------------------------------------------------
# _run_model() — treinamento, métricas e logging MLflow
# ---------------------------------------------------------------------------


def test_run_model_dry_run_returns_sentinel_id(fake_customers_df):
    """dry_run=True retorna 'dry-run-run-id' sem abrir run no MLflow."""
    from ml.models.random_forest.random_forest import _run_model

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    model = RandomForestClassifier(n_estimators=10, random_state=42, class_weight="balanced")

    with patch("ml.models.random_forest.random_forest._cv_metrics", return_value=_FAKE_METRICS):
        run_id, metrics = _run_model(model, X, y, dry_run=True, n_estimators=10, max_depth=None)

    assert run_id == "dry-run-run-id"
    assert metrics == _FAKE_METRICS


def test_run_model_dry_run_does_not_call_mlflow(fake_customers_df):
    """dry_run=True não deve chamar mlflow.start_run."""
    from ml.models.random_forest.random_forest import _run_model

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    model = RandomForestClassifier(n_estimators=10, random_state=42, class_weight="balanced")

    with patch("ml.models.random_forest.random_forest._cv_metrics", return_value=_FAKE_METRICS), \
         patch("ml.models.random_forest.random_forest.mlflow.start_run") as mock_start_run:
        _run_model(model, X, y, dry_run=True, n_estimators=10, max_depth=None)

    mock_start_run.assert_not_called()


def test_run_model_not_dry_run_logs_feature_importances(fake_customers_df):
    """dry_run=False loga métricas, params, artefato sklearn e feature_importances.json."""
    from ml.models.random_forest.random_forest import _run_model

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    model = RandomForestClassifier(n_estimators=10, random_state=42, class_weight="balanced")

    mock_run = MagicMock()
    mock_run.info.run_id = "mlflow-rf-456"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_run)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("ml.models.random_forest.random_forest._cv_metrics", return_value=_FAKE_METRICS), \
         patch("ml.models.random_forest.random_forest.mlflow.start_run", return_value=mock_ctx), \
         patch("ml.models.random_forest.random_forest.mlflow.log_params") as mock_log_params, \
         patch("ml.models.random_forest.random_forest.mlflow.log_metrics") as mock_log_metrics, \
         patch("ml.models.random_forest.random_forest.mlflow.log_artifacts") as mock_log_artifacts, \
         patch("ml.models.random_forest.random_forest.mlflow.log_dict") as mock_log_dict:
        run_id, metrics = _run_model(model, X, y, dry_run=False, n_estimators=10, max_depth=None)

    assert run_id == "mlflow-rf-456"
    assert metrics == _FAKE_METRICS
    mock_log_params.assert_called_once()
    mock_log_metrics.assert_called_once_with(_FAKE_METRICS)
    mock_log_artifacts.assert_called_once()
    assert mock_log_artifacts.call_args.kwargs["artifact_path"] == "model"
    mock_log_dict.assert_called_once()
    assert mock_log_dict.call_args[0][1] == "feature_importances.json"


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
    from ml.models.random_forest.random_forest import _next_version

    conn = _make_mock_conn(count=0)
    version = _next_version(conn, "global", None, None, "global-random-forest")
    assert version == "v1"


def test_next_version_increments_correctly():
    """Quando já existem 2 versões, retorna 'v3'."""
    from ml.models.random_forest.random_forest import _next_version

    conn = _make_mock_conn(count=2)
    version = _next_version(conn, "project", "t-uuid", "p-uuid", "ibm-telco-telco-churn-2018-random-forest")
    assert version == "v3"


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
    from ml.models.random_forest.random_forest import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.models.random_forest.random_forest._build_engine", return_value=mock_engine), \
         patch("ml.models.random_forest.random_forest._next_version", return_value="v1"):
        _register_in_db(
            name="global-random-forest",
            run_id="test-run-id",
            metrics=_FAKE_METRICS,
            scope="global",
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=True,
        )

    captured = capsys.readouterr()
    assert "dry-run" in captured.out
    assert "Nenhuma escrita realizada" in captured.out
    mock_conn.execute.assert_not_called()


def test_register_in_db_approved_status_executes_only_insert():
    """status='approved' executa apenas INSERT do novo modelo."""
    from ml.models.random_forest.random_forest import _register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with patch("ml.models.random_forest.random_forest._build_engine", return_value=mock_engine), \
         patch("ml.models.random_forest.random_forest._next_version", return_value="v1"):
        _register_in_db(
            name="global-random-forest",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="global",
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 1


def test_register_in_db_dry_run_includes_version_in_output(capsys):
    """O output do dry-run inclui a versão calculada."""
    from ml.models.random_forest.random_forest import _register_in_db

    mock_engine, _ = _make_mock_engine()

    with patch("ml.models.random_forest.random_forest._build_engine", return_value=mock_engine), \
         patch("ml.models.random_forest.random_forest._next_version", return_value="v2"):
        _register_in_db(
            name="ibm-telco-random-forest",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="tenant",
            tenant_slug="ibm-telco",
            project_slug=None,
            status="approved",
            dry_run=True,
        )

    assert "v2" in capsys.readouterr().out


def test_register_in_db_project_scope_calls_both_resolvers():
    """Escopo project chama _resolve_tenant_id e _resolve_project_id."""
    from ml.models.random_forest.random_forest import _register_in_db

    mock_engine, _ = _make_mock_engine()

    with patch("ml.models.random_forest.random_forest._build_engine", return_value=mock_engine), \
         patch("ml.models.random_forest.random_forest._next_version", return_value="v1"), \
         patch("ml.models.random_forest.random_forest._resolve_tenant_id", return_value="tenant-uuid") as mock_tid, \
         patch("ml.models.random_forest.random_forest._resolve_project_id", return_value="project-uuid") as mock_pid:
        _register_in_db(
            name="ibm-telco-telco-churn-2018-random-forest",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            scope="project",
            tenant_slug="ibm-telco",
            project_slug="telco-churn-2018",
            status="approved",
            dry_run=True,
        )

    mock_tid.assert_called()
    mock_pid.assert_called()


# ---------------------------------------------------------------------------
# main() — orquestração completa do pipeline de treinamento
# ---------------------------------------------------------------------------


def test_main_dry_run_calls_run_model_and_register(fake_customers_df):
    """main() com dry_run=True chama _run_model e _register_in_db uma vez cada."""
    from ml.models.random_forest.random_forest import main

    fake_args = argparse.Namespace(
        tenant=None, project=None, dry_run=True, n_estimators=10, max_depth=None
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.models.random_forest.random_forest._parse_args", return_value=fake_args), \
         patch("ml.models.random_forest.random_forest.load_data", return_value=(X, y)), \
         patch("ml.models.random_forest.random_forest._run_model", return_value=("dry-run-run-id", _FAKE_METRICS)) as mock_run, \
         patch("ml.models.random_forest.random_forest._register_in_db") as mock_register:
        main()

    mock_run.assert_called_once()
    mock_register.assert_called_once()


def test_main_always_marks_model_as_approved(fake_customers_df):
    """main() sempre registra o Random Forest com status='approved'."""
    from ml.models.random_forest.random_forest import main

    fake_args = argparse.Namespace(
        tenant="ibm-telco", project="telco-churn-2018", dry_run=False, n_estimators=10, max_depth=None
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.models.random_forest.random_forest._parse_args", return_value=fake_args), \
         patch("ml.models.random_forest.random_forest.load_data", return_value=(X, y)), \
         patch("ml.models.random_forest.random_forest._run_model", return_value=("mlflow-rf-123", _FAKE_METRICS)), \
         patch("ml.models.random_forest.random_forest._register_in_db") as mock_register, \
         patch("ml.models.random_forest.random_forest.mlflow.set_tracking_uri"), \
         patch("ml.models.random_forest.random_forest.mlflow.set_experiment"):
        main()

    call_kwargs = mock_register.call_args.kwargs
    assert call_kwargs["status"] == "approved"


def test_main_dry_run_does_not_configure_mlflow(fake_customers_df):
    """main() com dry_run=True não chama mlflow.set_tracking_uri nem set_experiment."""
    from ml.models.random_forest.random_forest import main

    fake_args = argparse.Namespace(
        tenant=None, project=None, dry_run=True, n_estimators=10, max_depth=None
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.models.random_forest.random_forest._parse_args", return_value=fake_args), \
         patch("ml.models.random_forest.random_forest.load_data", return_value=(X, y)), \
         patch("ml.models.random_forest.random_forest._run_model", return_value=("dry-run-run-id", _FAKE_METRICS)), \
         patch("ml.models.random_forest.random_forest._register_in_db"), \
         patch("ml.models.random_forest.random_forest.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.models.random_forest.random_forest.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_not_called()
    mock_exp.assert_not_called()


def test_main_not_dry_run_configures_mlflow(fake_customers_df):
    """main() sem dry_run chama mlflow.set_tracking_uri e set_experiment."""
    from ml.models.random_forest.random_forest import main

    fake_args = argparse.Namespace(
        tenant="ibm-telco", project="telco-churn-2018", dry_run=False, n_estimators=10, max_depth=None
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.models.random_forest.random_forest._parse_args", return_value=fake_args), \
         patch("ml.models.random_forest.random_forest.load_data", return_value=(X, y)), \
         patch("ml.models.random_forest.random_forest._run_model", return_value=("mlflow-rf-123", _FAKE_METRICS)), \
         patch("ml.models.random_forest.random_forest._register_in_db"), \
         patch("ml.models.random_forest.random_forest.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.models.random_forest.random_forest.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_called_once()
    mock_exp.assert_called_once_with("ibm-telco/telco-churn-2018/random-forest")
