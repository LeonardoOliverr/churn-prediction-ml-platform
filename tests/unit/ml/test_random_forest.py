"""
Testes para o comportamento de Random Forest no CLI unificado (ml/train.py).

Inclui:
- [SMOKE TEST] Pipeline mínimo: preprocess → fit → predict sem DB ou MLflow
- Testes da interface sklearn do RandomForestClassifier
- Testes das funções puras: _derive_scope(), _db_name()
- Testes de _parse_args() com --model random_forest
- Testes de main() para comportamento de random_forest (sempre approved)
"""

import argparse
import sys

import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from unittest.mock import MagicMock, patch

from ml.config.settings import TARGET
from ml.data.preprocessing import build_preprocessor


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
# _derive_scope() — retorna 2-tupla (scope, experiment_name)
# ---------------------------------------------------------------------------


def test_derive_scope_global():
    """(None, None) → escopo global, experimento global/random-forest."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope(None, None, "random-forest")
    assert scope == "global"
    assert experiment == "global/random-forest"


def test_derive_scope_tenant():
    """(slug, None) → escopo tenant, experimento contém o slug."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", None, "random-forest")
    assert scope == "tenant"
    assert "ibm-telco" in experiment
    assert "random-forest" in experiment


def test_derive_scope_project():
    """(slug, slug) → escopo project, experimento contém tenant e projeto."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", "telco-churn-2018", "random-forest")
    assert scope == "project"
    assert "ibm-telco" in experiment
    assert "telco-churn-2018" in experiment


def test_derive_scope_returns_two_tuple():
    """_derive_scope retorna sempre uma tupla de 2 elementos."""
    from ml.train import _derive_scope

    for args in [(None, None, "random-forest"), ("t", None, "random-forest"), ("t", "p", "random-forest")]:
        result = _derive_scope(*args)
        assert len(result) == 2, f"Esperado 2-tuple, got {len(result)}-tuple para {args}"


# ---------------------------------------------------------------------------
# _db_name() — gera o nome do modelo para registro em churn.models
# ---------------------------------------------------------------------------


def test_db_name_global():
    """Qualquer escopo → apenas nome do modelo em kebab-case."""
    from ml.train import _db_name

    assert _db_name("random_forest") == "random-forest"


def test_db_name_tenant():
    """Qualquer escopo → apenas nome do modelo em kebab-case."""
    from ml.train import _db_name

    assert _db_name("random_forest") == "random-forest"


def test_db_name_project():
    """Qualquer escopo → apenas nome do modelo em kebab-case."""
    from ml.train import _db_name

    assert _db_name("random_forest") == "random-forest"


# ---------------------------------------------------------------------------
# _parse_args() — parsing de argumentos CLI com --model random_forest
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    """Sem argumentos opcionais → tenant=None, project=None, dry_run=False, n_estimators=500, max_depth=None."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest"]):
        args = _parse_args()

    assert args.tenant is None
    assert args.project is None
    assert args.dry_run is False
    assert args.n_estimators == 500
    assert args.max_depth is None


def test_parse_args_n_estimators():
    """--n-estimators sobrescreve o default de 500."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest", "--n-estimators", "300"]):
        args = _parse_args()

    assert args.n_estimators == 300


def test_parse_args_max_depth():
    """--max-depth define a profundidade máxima."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest", "--max-depth", "10"]):
        args = _parse_args()

    assert args.max_depth == 10


def test_parse_args_dry_run_flag():
    """--dry-run ativa o modo de simulação."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest", "--dry-run"]):
        args = _parse_args()

    assert args.dry_run is True


def test_parse_args_project_without_tenant_exits():
    """--project sem --tenant deve encerrar com SystemExit."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest", "--project", "telco-churn-2018"]):
        with pytest.raises(SystemExit):
            _parse_args()


# ---------------------------------------------------------------------------
# main() — orquestração completa do pipeline de treinamento
# ---------------------------------------------------------------------------


def test_main_dry_run_calls_train_with_cv_and_register(fake_customers_df):
    """main() com dry_run=True chama train_with_cv e register_in_db uma vez cada."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant=None, project=None, dry_run=True,
        holdout_size=0.2, n_estimators=10, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    mock_pipeline = MagicMock()

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": mock_pipeline, "metrics": _FAKE_METRICS}) as mock_train, \
         patch("ml.train.register_in_db") as mock_register:
        main()

    mock_train.assert_called_once()
    mock_register.assert_called_once()
    register_kwargs = mock_register.call_args.kwargs
    assert register_kwargs["hyperparameters"]["n_estimators"] == 10
    assert register_kwargs["hyperparameters"]["max_features"] == "sqrt"
    assert register_kwargs["training_params"]["holdout_size"] == 0.2
    assert register_kwargs["training_params"]["primary_metric"] == "f1"


def test_main_always_marks_model_as_approved(fake_customers_df):
    """main() sempre registra o Random Forest com status='approved'."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant="ibm-telco", project="telco-churn-2018", dry_run=False,
        holdout_size=0.2, n_estimators=10, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    mock_pipeline = MagicMock()

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": mock_pipeline, "metrics": _FAKE_METRICS}), \
         patch("ml.train.log_to_mlflow", return_value="mlflow-rf-123"), \
         patch("ml.train.register_in_db") as mock_register, \
         patch("ml.train.mlflow.set_tracking_uri"), \
         patch("ml.train.mlflow.set_experiment"):
        main()

    call_kwargs = mock_register.call_args.kwargs
    assert call_kwargs["status"] == "approved"


def test_main_dry_run_does_not_configure_mlflow(fake_customers_df):
    """main() com dry_run=True não chama mlflow.set_tracking_uri nem set_experiment."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant=None, project=None, dry_run=True,
        holdout_size=0.2, n_estimators=10, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    mock_pipeline = MagicMock()

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": mock_pipeline, "metrics": _FAKE_METRICS}), \
         patch("ml.train.register_in_db"), \
         patch("ml.train.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.train.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_not_called()
    mock_exp.assert_not_called()


def test_main_not_dry_run_configures_mlflow(fake_customers_df):
    """main() sem dry_run chama mlflow.set_tracking_uri e set_experiment."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant="ibm-telco", project="telco-churn-2018", dry_run=False,
        holdout_size=0.2, n_estimators=10, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    mock_pipeline = MagicMock()

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": mock_pipeline, "metrics": _FAKE_METRICS}), \
         patch("ml.train.log_to_mlflow", return_value="mlflow-rf-123"), \
         patch("ml.train.register_in_db"), \
         patch("ml.train.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.train.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_called_once()
    mock_exp.assert_called_once_with("ibm-telco/telco-churn-2018/random-forest")
