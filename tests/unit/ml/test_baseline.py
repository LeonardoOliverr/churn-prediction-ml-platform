"""
Testes para o comportamento de baseline no CLI unificado (ml/train.py).

Inclui:
- [SMOKE TEST] Pipeline mínimo: preprocess → fit → predict sem DB ou MLflow
- Testes da interface sklearn dos estimadores configurados via _resolve_specs
- Testes das funções puras: _derive_scope() e _db_name()
- Testes de _parse_args() com --model baseline
- Testes de main() para comportamento de baseline (seleção por melhor F1)
"""

import argparse
import sys
from unittest.mock import MagicMock, patch

import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.config.settings import TARGET
from ml.data.preprocessing import build_preprocessor

_FAKE_METRICS = {
    "f1_mean": 0.65,
    "f1_std": 0.04,
    "roc_auc_mean": 0.85,
    "roc_auc_std": 0.02,
    "recall_mean": 0.80,
    "recall_std": 0.04,
    "precision_mean": 0.70,
    "precision_std": 0.03,
    "train_f1_mean": 0.82,
    "train_roc_auc_mean": 0.94,
    "train_recall_mean": 0.89,
    "train_precision_mean": 0.78,
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
# Interface sklearn dos estimadores retornados por _resolve_specs("baseline")
# ---------------------------------------------------------------------------


def test_baseline_specs_have_fit_method():
    """Todos os estimadores de baseline possuem método fit."""
    from ml.train import _resolve_specs

    for spec in _resolve_specs("baseline"):
        estimator = spec.estimator_factory()
        assert hasattr(estimator, "fit"), f"Spec '{spec.name}' não tem método fit."


def test_baseline_specs_have_predict_method():
    """Todos os estimadores de baseline possuem método predict."""
    from ml.train import _resolve_specs

    for spec in _resolve_specs("baseline"):
        estimator = spec.estimator_factory()
        assert hasattr(estimator, "predict"), f"Spec '{spec.name}' não tem método predict."


def test_baseline_specs_have_predict_proba_method():
    """Todos os estimadores de baseline possuem método predict_proba."""
    from ml.train import _resolve_specs

    for spec in _resolve_specs("baseline"):
        estimator = spec.estimator_factory()
        assert hasattr(estimator, "predict_proba"), (
            f"Spec '{spec.name}' não tem método predict_proba."
        )


def test_baseline_specs_contain_expected_names():
    """_resolve_specs('baseline') retorna dummy_stratified e logistic_regression."""
    from ml.train import _resolve_specs

    names = [spec.name for spec in _resolve_specs("baseline")]
    assert "dummy_stratified" in names
    assert "logistic_regression" in names


# ---------------------------------------------------------------------------
# _derive_scope() — função pura, retorna 2-tupla
# ---------------------------------------------------------------------------


def test_derive_scope_global():
    """(None, None) → escopo global."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope(None, None, "baseline")
    assert scope == "global"
    assert experiment == "global/baseline"


def test_derive_scope_tenant():
    """(slug, None) → escopo tenant."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", None, "baseline")
    assert scope == "tenant"
    assert "ibm-telco" in experiment


def test_derive_scope_project():
    """(slug, slug) → escopo project."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", "telco-churn-2018", "baseline")
    assert scope == "project"
    assert "ibm-telco" in experiment
    assert "telco-churn-2018" in experiment


def test_derive_scope_returns_two_tuple():
    """_derive_scope retorna sempre uma tupla de 2 elementos."""
    from ml.train import _derive_scope

    for args, expected_scope in [
        ((None, None, "baseline"), "global"),
        (("slug", None, "baseline"), "tenant"),
        (("slug", "proj", "baseline"), "project"),
    ]:
        scope, _ = _derive_scope(*args)
        assert scope == expected_scope


# ---------------------------------------------------------------------------
# _parse_args() — parsing de argumentos CLI com --model baseline
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    """Sem argumentos opcionais → tenant=None, project=None, dry_run=False."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline"]):
        args = _parse_args()

    assert args.tenant is None
    assert args.project is None
    assert args.dry_run is False


def test_parse_args_tenant_only():
    """--tenant define tenant sem afetar project ou dry_run."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline", "--tenant", "ibm-telco"]):
        args = _parse_args()

    assert args.tenant == "ibm-telco"
    assert args.project is None
    assert args.dry_run is False


def test_parse_args_tenant_and_project():
    """--tenant + --project definem ambos os escopos."""
    from ml.train import _parse_args

    with patch.object(
        sys,
        "argv",
        [
            "train.py",
            "--model",
            "baseline",
            "--tenant",
            "ibm-telco",
            "--project",
            "telco-churn-2018",
        ],
    ):
        args = _parse_args()

    assert args.tenant == "ibm-telco"
    assert args.project == "telco-churn-2018"


def test_parse_args_dry_run_flag():
    """--dry-run ativa o modo de simulação."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline", "--dry-run"]):
        args = _parse_args()

    assert args.dry_run is True


def test_parse_args_project_without_tenant_exits():
    """--project sem --tenant deve encerrar com SystemExit."""
    from ml.train import _parse_args

    with patch.object(
        sys, "argv", ["train.py", "--model", "baseline", "--project", "telco-churn-2018"]
    ):
        with pytest.raises(SystemExit):
            _parse_args()


# ---------------------------------------------------------------------------
# main() — orquestração completa do pipeline de treinamento
# ---------------------------------------------------------------------------


def _fake_train_with_cv_side_effect(spec, X, y, hp_overrides=None, holdout_size=0.2):
    """Retorna métricas diferentes por modelo para simular comparação realista."""
    if spec.name == "logistic_regression":
        return {"pipeline": MagicMock(), "metrics": _FAKE_METRICS}
    return {"pipeline": MagicMock(), "metrics": _DUMMY_METRICS}


def test_main_dry_run_calls_train_with_cv_for_each_spec(fake_customers_df):
    """main() com dry_run=True chama train_with_cv e register_in_db para cada spec."""
    from ml.train import _resolve_specs, main

    fake_args = argparse.Namespace(
        model="baseline",
        tenant=None,
        project=None,
        dry_run=True,
        holdout_size=0.2,
        n_estimators=500,
        max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch("ml.train.train_with_cv", side_effect=_fake_train_with_cv_side_effect) as mock_train,
        patch("ml.train.register_in_db") as mock_register,
    ):
        main()

    n_specs = len(_resolve_specs("baseline"))
    assert mock_train.call_count == n_specs
    assert mock_register.call_count == n_specs


def test_main_dry_run_does_not_configure_mlflow(fake_customers_df):
    """main() com dry_run=True não chama mlflow.set_tracking_uri nem set_experiment."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="baseline",
        tenant=None,
        project=None,
        dry_run=True,
        holdout_size=0.2,
        n_estimators=500,
        max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch("ml.train.train_with_cv", side_effect=_fake_train_with_cv_side_effect),
        patch("ml.train.register_in_db"),
        patch("ml.train.mlflow.set_tracking_uri") as mock_uri,
        patch("ml.train.mlflow.set_experiment") as mock_exp,
    ):
        main()

    mock_uri.assert_not_called()
    mock_exp.assert_not_called()


def test_main_not_dry_run_marks_best_model_as_approved(fake_customers_df):
    """main() sem dry_run registra todos os modelos como 'candidate' aguardando aprovação humana."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="baseline",
        tenant=None,
        project=None,
        dry_run=False,
        holdout_size=0.2,
        n_estimators=500,
        max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch("ml.train.train_with_cv", side_effect=_fake_train_with_cv_side_effect),
        patch("ml.train.log_to_mlflow", return_value="run-id"),
        patch("ml.train.register_in_db") as mock_register,
        patch("ml.train.mlflow.set_tracking_uri"),
        patch("ml.train.mlflow.set_experiment"),
    ):
        main()

    statuses = {c.kwargs["name"]: c.kwargs["status"] for c in mock_register.call_args_list}
    assert statuses["logistic-regression"] == "candidate"
    assert statuses["dummy-stratified"] == "candidate"


def test_main_not_dry_run_configures_mlflow(fake_customers_df):
    """main() sem dry_run chama mlflow.set_tracking_uri e set_experiment."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="baseline",
        tenant="ibm-telco",
        project=None,
        dry_run=False,
        holdout_size=0.2,
        n_estimators=500,
        max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch("ml.train.train_with_cv", side_effect=_fake_train_with_cv_side_effect),
        patch("ml.train.log_to_mlflow", return_value="run-id"),
        patch("ml.train.register_in_db"),
        patch("ml.train.mlflow.set_tracking_uri") as mock_uri,
        patch("ml.train.mlflow.set_experiment") as mock_exp,
    ):
        main()

    mock_uri.assert_called_once()
    mock_exp.assert_called_once_with("ibm-telco/baseline")
