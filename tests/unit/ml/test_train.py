"""
Testes unitários para ml/train.py (CLI unificado).

Inclui:
- _parse_args(): argumentos obrigatórios, holdout_size, n_estimators, max_depth
- _resolve_specs(): retorno correto por modelo
- _derive_scope(): 2-tupla para cada nível de escopo
- _db_name(): geração de nomes compatíveis com os scripts legados
- main(): comportamentos de dry-run, seleção de modelo e configuração MLflow
"""

import argparse
import sys

import pytest
from unittest.mock import MagicMock, patch

from ml.config.settings import TARGET


_FAKE_METRICS = {
    "f1_mean": 0.71, "f1_std": 0.0,
    "roc_auc_mean": 0.90, "roc_auc_std": 0.0,
    "recall_mean": 0.83, "recall_std": 0.0,
    "precision_mean": 0.63, "precision_std": 0.0,
    "train_f1_mean": 0.98, "train_roc_auc_mean": 0.99,
    "train_recall_mean": 0.97, "train_precision_mean": 0.98,
}


# ---------------------------------------------------------------------------
# _parse_args()
# ---------------------------------------------------------------------------


def test_parse_args_requires_model():
    """Sem --model, deve encerrar com SystemExit."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py"]):
        with pytest.raises(SystemExit):
            _parse_args()


def test_parse_args_model_baseline():
    """--model baseline define args.model corretamente."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline"]):
        args = _parse_args()

    assert args.model == "baseline"


def test_parse_args_model_random_forest():
    """--model random_forest define args.model corretamente."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest"]):
        args = _parse_args()

    assert args.model == "random_forest"


def test_parse_args_holdout_size_defaults_to_0_2():
    """--holdout-size padrão é 0.2."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline"]):
        args = _parse_args()

    assert args.holdout_size == 0.2


def test_parse_args_holdout_size_custom():
    """--holdout-size aceita valor customizado."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline", "--holdout-size", "0.3"]):
        args = _parse_args()

    assert args.holdout_size == 0.3


def test_parse_args_holdout_size_zero_disables_holdout():
    """--holdout-size 0.0 desativa o holdout (CV puro)."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "baseline", "--holdout-size", "0.0"]):
        args = _parse_args()

    assert args.holdout_size == 0.0


def test_parse_args_n_estimators_default():
    """--n-estimators padrão é 500."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest"]):
        args = _parse_args()

    assert args.n_estimators == 500


def test_parse_args_max_depth_default_is_none():
    """--max-depth padrão é None."""
    from ml.train import _parse_args

    with patch.object(sys, "argv", ["train.py", "--model", "random_forest"]):
        args = _parse_args()

    assert args.max_depth is None


# ---------------------------------------------------------------------------
# _resolve_specs()
# ---------------------------------------------------------------------------


def test_resolve_specs_baseline_returns_two_specs():
    """_resolve_specs('baseline') retorna exatamente 2 specs."""
    from ml.train import _resolve_specs

    specs = _resolve_specs("baseline")
    assert len(specs) == 2


def test_resolve_specs_baseline_names():
    """_resolve_specs('baseline') retorna dummy_stratified e logistic_regression."""
    from ml.train import _resolve_specs

    names = [s.name for s in _resolve_specs("baseline")]
    assert "dummy_stratified" in names
    assert "logistic_regression" in names


def test_resolve_specs_random_forest_returns_one_spec():
    """_resolve_specs('random_forest') retorna exatamente 1 spec."""
    from ml.train import _resolve_specs

    specs = _resolve_specs("random_forest")
    assert len(specs) == 1


def test_resolve_specs_random_forest_has_feature_importances():
    """Spec de random_forest tem log_feature_importances=True."""
    from ml.train import _resolve_specs

    spec = _resolve_specs("random_forest")[0]
    assert spec.log_feature_importances is True


def test_resolve_specs_baseline_has_no_cli_overrides():
    """Specs de baseline não têm cli_overrides."""
    from ml.train import _resolve_specs

    for spec in _resolve_specs("baseline"):
        assert spec.cli_overrides == {}


def test_resolve_specs_random_forest_has_cli_overrides():
    """Spec de random_forest tem cli_overrides com n_estimators e max_depth."""
    from ml.train import _resolve_specs

    spec = _resolve_specs("random_forest")[0]
    assert "n_estimators" in spec.cli_overrides
    assert "max_depth" in spec.cli_overrides


def test_resolve_specs_unknown_model_raises():
    """Modelo desconhecido levanta ValueError."""
    from ml.train import _resolve_specs

    with pytest.raises(ValueError):
        _resolve_specs("xgboost")


# ---------------------------------------------------------------------------
# _derive_scope()
# ---------------------------------------------------------------------------


def test_derive_scope_global():
    """(None, None) → escopo global."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope(None, None, "random-forest")
    assert scope == "global"
    assert experiment == "global/random-forest"


def test_derive_scope_tenant():
    """(slug, None) → escopo tenant."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", None, "random-forest")
    assert scope == "tenant"
    assert "ibm-telco" in experiment


def test_derive_scope_project():
    """(slug, slug) → escopo project."""
    from ml.train import _derive_scope

    scope, experiment = _derive_scope("ibm-telco", "telco-churn-2018", "random-forest")
    assert scope == "project"
    assert "ibm-telco" in experiment
    assert "telco-churn-2018" in experiment


# ---------------------------------------------------------------------------
# _db_name()
# ---------------------------------------------------------------------------


def test_db_name_global_baseline():
    from ml.train import _db_name
    assert _db_name("global", None, None, "logistic_regression") == "global-logistic-regression"


def test_db_name_global_rf():
    from ml.train import _db_name
    assert _db_name("global", None, None, "random_forest") == "global-random-forest"


def test_db_name_project_rf():
    from ml.train import _db_name
    assert _db_name("project", "ibm-telco", "telco-churn-2018", "random_forest") == "ibm-telco-telco-churn-2018-random-forest"


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_dry_run_does_not_call_log_to_mlflow(fake_customers_df):
    """main() com dry_run=True não chama log_to_mlflow."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant=None, project=None, dry_run=True,
        holdout_size=0.2, n_estimators=500, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS}), \
         patch("ml.train.log_to_mlflow") as mock_log, \
         patch("ml.train.register_in_db"):
        main()

    mock_log.assert_not_called()


def test_main_not_dry_run_calls_log_to_mlflow(fake_customers_df):
    """main() sem dry_run chama log_to_mlflow para cada spec."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant=None, project=None, dry_run=False,
        holdout_size=0.2, n_estimators=500, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS}), \
         patch("ml.train.log_to_mlflow", return_value="run-id") as mock_log, \
         patch("ml.train.register_in_db"), \
         patch("ml.train.mlflow.set_tracking_uri"), \
         patch("ml.train.mlflow.set_experiment"):
        main()

    mock_log.assert_called_once()


def test_main_calls_comparison_report_and_registration(fake_customers_df):
    """main() orquestra comparacao, relatorio e registro apos treinar candidatos."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="baseline", tenant=None, project=None, dry_run=True,
        holdout_size=0.2, n_estimators=500, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    fake_comparison = MagicMock()

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS}), \
         patch("ml.train.compare_results", return_value=fake_comparison) as mock_compare, \
         patch("ml.train.build_run_report", return_value="report") as mock_report, \
         patch("ml.train._register_comparison") as mock_register:
        main()

    mock_compare.assert_called_once()
    mock_report.assert_called_once()
    mock_register.assert_called_once()
    assert mock_report.call_args.kwargs["comparison"] is fake_comparison
    assert mock_register.call_args.kwargs["comparison"] is fake_comparison


def test_main_passes_holdout_size_to_train_with_cv(fake_customers_df):
    """main() repassa holdout_size ao train_with_cv."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="baseline", tenant=None, project=None, dry_run=True,
        holdout_size=0.3, n_estimators=500, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS}) as mock_train, \
         patch("ml.train.register_in_db"):
        main()

    for call in mock_train.call_args_list:
        assert call.kwargs.get("holdout_size") == 0.3 or call.args[3] == 0.3 or call.kwargs.get("holdout_size") == 0.3


def test_main_dry_run_does_not_configure_mlflow(fake_customers_df):
    """main() com dry_run=True não chama mlflow.set_tracking_uri nem set_experiment."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="random_forest", tenant=None, project=None, dry_run=True,
        holdout_size=0.2, n_estimators=500, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS}), \
         patch("ml.train.register_in_db"), \
         patch("ml.train.mlflow.set_tracking_uri") as mock_uri, \
         patch("ml.train.mlflow.set_experiment") as mock_exp:
        main()

    mock_uri.assert_not_called()
    mock_exp.assert_not_called()


def test_main_not_dry_run_configures_mlflow_for_baseline(fake_customers_df):
    """main() sem dry_run chama set_experiment com experimento correto para baseline."""
    from ml.train import main

    fake_args = argparse.Namespace(
        model="baseline", tenant="ibm-telco", project=None, dry_run=False,
        holdout_size=0.2, n_estimators=500, max_depth=None,
    )
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.train._parse_args", return_value=fake_args), \
         patch("ml.train.load_data", return_value=(X, y)), \
         patch("ml.train.train_with_cv", return_value={"pipeline": MagicMock(), "metrics": _FAKE_METRICS}), \
         patch("ml.train.log_to_mlflow", return_value="run-id"), \
         patch("ml.train.register_in_db"), \
         patch("ml.train.mlflow.set_tracking_uri"), \
         patch("ml.train.mlflow.set_experiment") as mock_exp:
        main()

    mock_exp.assert_called_once_with("ibm-telco/baseline")
