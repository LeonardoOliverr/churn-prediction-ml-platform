"""
Testes para o comportamento de XGBoost no CLI unificado (ml/train.py).

Inclui:
- [SMOKE TEST] Pipeline mínimo: preprocess → fit → predict sem DB ou MLflow
- Testes da interface sklearn do XGBClassifier
- Testes de _resolve_specs() com --model xgboost
- Testes de _parse_args() com --model xgboost
- Testes de main() para comportamento de xgboost
"""

import argparse
import sys
from unittest.mock import MagicMock, patch

import pytest
from sklearn.pipeline import Pipeline

from ml.config.settings import TARGET
from ml.data.preprocessing import build_preprocessor

_FAKE_METRICS = {
    "f1_mean": 0.67,
    "f1_std": 0.01,
    "roc_auc_mean": 0.87,
    "roc_auc_std": 0.01,
    "recall_mean": 0.81,
    "recall_std": 0.02,
    "precision_mean": 0.57,
    "precision_std": 0.02,
    "train_f1_mean": 0.72,
    "train_roc_auc_mean": 0.91,
    "train_recall_mean": 0.78,
    "train_precision_mean": 0.68,
}


# ---------------------------------------------------------------------------
# SMOKE TEST — fluxo mínimo end-to-end sem dependências externas
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_smoke_pipeline_xgboost(fake_customers_df):
    """[SMOKE TEST] XGBClassifier treina e prediz sem erros com dados fake."""
    from xgboost import XGBClassifier

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=10,
                    max_depth=3,
                    random_state=42,
                    eval_metric="auc",
                    objective="binary:logistic",
                ),
            ),
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
# Interface sklearn do XGBClassifier
# ---------------------------------------------------------------------------


def test_xgboost_has_fit_method():
    """XGBClassifier possui método fit."""
    from xgboost import XGBClassifier

    model = XGBClassifier(n_estimators=10, random_state=42)
    assert hasattr(model, "fit")


def test_xgboost_has_predict_proba_method():
    """XGBClassifier possui método predict_proba."""
    from xgboost import XGBClassifier

    model = XGBClassifier(n_estimators=10, random_state=42)
    assert hasattr(model, "predict_proba")


def test_xgboost_has_feature_importances_after_fit(fake_customers_df):
    """Após fit, feature_importances_ está disponível."""
    from xgboost import XGBClassifier

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=10,
                    random_state=42,
                    eval_metric="auc",
                    objective="binary:logistic",
                ),
            ),
        ]
    )
    pipeline.fit(X, y)

    importances = pipeline.named_steps["classifier"].feature_importances_
    assert importances is not None
    assert len(importances) > 0


# ---------------------------------------------------------------------------
# _resolve_specs("xgboost")
# ---------------------------------------------------------------------------


def test_resolve_specs_xgboost_returns_one_spec():
    """_resolve_specs('xgboost') retorna exatamente 1 spec."""
    from ml.train import _resolve_specs

    specs = _resolve_specs("xgboost")
    assert len(specs) == 1


def test_resolve_specs_xgboost_name():
    """Spec de xgboost tem name='xgboost'."""
    from ml.train import _resolve_specs

    spec = _resolve_specs("xgboost")[0]
    assert spec.name == "xgboost"


def test_resolve_specs_xgboost_has_feature_importances():
    """Spec de xgboost tem log_feature_importances=True."""
    from ml.train import _resolve_specs

    spec = _resolve_specs("xgboost")[0]
    assert spec.log_feature_importances is True


def test_resolve_specs_xgboost_has_cli_overrides():
    """Spec de xgboost expõe hiperparâmetros via cli_overrides."""
    from ml.train import _resolve_specs

    spec = _resolve_specs("xgboost")[0]
    assert "n_estimators" in spec.cli_overrides
    assert "max_depth" in spec.cli_overrides
    assert "learning_rate" in spec.cli_overrides
    assert "reg_alpha" in spec.cli_overrides
    assert "reg_lambda" in spec.cli_overrides


def test_resolve_specs_xgboost_default_params_have_regularization():
    """Spec de xgboost tem parâmetros de regularização nos defaults."""
    from ml.train import _resolve_specs

    spec = _resolve_specs("xgboost")[0]
    assert "reg_alpha" in spec.default_params
    assert "reg_lambda" in spec.default_params
    assert "subsample" in spec.default_params


# ---------------------------------------------------------------------------
# _parse_args() com --model xgboost
# ---------------------------------------------------------------------------


def test_parse_args_model_xgboost():
    """--model xgboost define args.model corretamente."""
    from ml.train import _parse_args

    with patch.object(
        sys,
        "argv",
        [
            "train.py",
            "--model",
            "xgboost",
            "--tenant",
            "ibm-telco",
            "--project",
            "telco-churn-2018",
        ],
    ):
        args = _parse_args()

    assert args.model == "xgboost"


def test_parse_args_xgboost_learning_rate():
    """--learning-rate é aceito e parseado como float."""
    from ml.train import _parse_args

    with patch.object(
        sys,
        "argv",
        [
            "train.py",
            "--model",
            "xgboost",
            "--tenant",
            "ibm-telco",
            "--project",
            "telco-churn-2018",
            "--learning-rate",
            "0.01",
        ],
    ):
        args = _parse_args()

    assert args.learning_rate == 0.01


def test_parse_args_xgboost_regularization_params():
    """--reg-alpha e --reg-lambda são aceitos como float."""
    from ml.train import _parse_args

    with patch.object(
        sys,
        "argv",
        [
            "train.py",
            "--model",
            "xgboost",
            "--tenant",
            "ibm-telco",
            "--project",
            "telco-churn-2018",
            "--reg-alpha",
            "0.5",
            "--reg-lambda",
            "3.0",
        ],
    ):
        args = _parse_args()

    assert args.reg_alpha == 0.5
    assert args.reg_lambda == 3.0


# ---------------------------------------------------------------------------
# main() com model=xgboost
# ---------------------------------------------------------------------------


def test_main_xgboost_registers_as_candidate(fake_customers_df):
    """main() com model=xgboost registra o modelo com status='candidate'."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="xgboost",
        tenant="ibm-telco",
        project="telco-churn-2018",
        dry_run=False,
        holdout_size=0.2,
        n_estimators=10,
        max_depth=3,
        learning_rate=None,
        subsample=None,
        colsample_bytree=None,
        scale_pos_weight=None,
        reg_alpha=None,
        reg_lambda=None,
        min_child_weight=None,
        gamma=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch(
            "ml.train.train_with_cv",
            return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS},
        ),
        patch("ml.train.log_to_mlflow", return_value="mlflow-xgb-123"),
        patch("ml.train.register_in_db") as mock_register,
        patch("ml.train.mlflow.set_tracking_uri"),
        patch("ml.train.mlflow.set_experiment"),
    ):
        main()

    call_kwargs = mock_register.call_args.kwargs
    assert call_kwargs["status"] == "candidate"
    assert call_kwargs["name"] == "xgboost"


def test_main_xgboost_configures_mlflow_experiment(fake_customers_df):
    """main() com model=xgboost chama set_experiment com o experimento correto."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="xgboost",
        tenant="ibm-telco",
        project="telco-churn-2018",
        dry_run=False,
        holdout_size=0.2,
        n_estimators=10,
        max_depth=3,
        learning_rate=None,
        subsample=None,
        colsample_bytree=None,
        scale_pos_weight=None,
        reg_alpha=None,
        reg_lambda=None,
        min_child_weight=None,
        gamma=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch(
            "ml.train.train_with_cv",
            return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS},
        ),
        patch("ml.train.log_to_mlflow", return_value="mlflow-xgb-123"),
        patch("ml.train.register_in_db"),
        patch("ml.train.mlflow.set_tracking_uri"),
        patch("ml.train.mlflow.set_experiment") as mock_exp,
    ):
        main()

    mock_exp.assert_called_once_with("ibm-telco/telco-churn-2018/xgboost")


def test_main_xgboost_dry_run_skips_mlflow(fake_customers_df):
    """main() com model=xgboost e dry_run=True não chama log_to_mlflow."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="xgboost",
        tenant="ibm-telco",
        project="telco-churn-2018",
        dry_run=True,
        holdout_size=0.2,
        n_estimators=10,
        max_depth=3,
        learning_rate=None,
        subsample=None,
        colsample_bytree=None,
        scale_pos_weight=None,
        reg_alpha=None,
        reg_lambda=None,
        min_child_weight=None,
        gamma=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with (
        patch("ml.train._parse_args", return_value=fake_args),
        patch("ml.train.load_data", return_value=(X, y)),
        patch(
            "ml.train.train_with_cv",
            return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS},
        ),
        patch("ml.train.log_to_mlflow") as mock_log,
        patch("ml.train.register_in_db"),
    ):
        main()

    mock_log.assert_not_called()
