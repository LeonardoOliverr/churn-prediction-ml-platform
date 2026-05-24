"""
Testes unitários para ml/tools/compare_models.py.

Cobre funções puras e lógica de roteamento sem MLflow real nem display gráfico.
"""

import matplotlib

matplotlib.use("Agg")  # backend sem display — deve ser setado antes do primeiro import de pyplot

import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixture — DataFrame mínimo para testes de plot
# ---------------------------------------------------------------------------


def _make_df(n: int = 2) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model": ["Logistic Regression", "Random Forest"][:n],
            "order": [2, 3][:n],
            "experiment": ["tenant/proj/lr", "tenant/proj/rf"][:n],
            "run_id": ["run-1", "run-2"][:n],
            "f1_mean": [0.65, 0.72][:n],
            "f1_std": [0.02, 0.01][:n],
            "roc_auc_mean": [0.82, 0.89][:n],
            "recall_mean": [0.78, 0.85][:n],
            "precision_mean": [0.70, 0.76][:n],
            "train_f1_mean": [0.70, 0.75][:n],
            "train_roc_auc_mean": [0.85, 0.91][:n],
        }
    )


@pytest.fixture(autouse=True)
def _close_figs():
    """Fecha figuras matplotlib após cada teste para evitar vazamento de memória."""
    yield
    import matplotlib.pyplot as plt

    plt.close("all")


# ---------------------------------------------------------------------------
# _model_label
# ---------------------------------------------------------------------------


def test_model_label_uses_run_name_tag():
    """Usa mlflow.runName quando presente na tag."""
    from ml.tools.compare_models import _model_label

    run = MagicMock()
    run.data.tags = {"mlflow.runName": "random_forest_v2"}
    assert _model_label(run, "tenant/proj/exp") == "Random Forest V2"


def test_model_label_falls_back_to_experiment_name():
    """Sem tag, extrai nome da última parte do experiment_name."""
    from ml.tools.compare_models import _model_label

    run = MagicMock()
    run.data.tags = {}
    assert _model_label(run, "tenant/proj/random-forest") == "Random Forest"


# ---------------------------------------------------------------------------
# _line_df
# ---------------------------------------------------------------------------


def test_line_df_sorts_by_order_then_f1_desc():
    """Ordena por order ASC, f1_mean DESC dentro do mesmo order."""
    from ml.tools.compare_models import _line_df

    df = pd.DataFrame(
        {
            "model": ["RF-low", "LR", "RF-high"],
            "order": [3, 2, 3],
            "f1_mean": [0.70, 0.65, 0.75],
        }
    )
    result = _line_df(df)
    assert result.iloc[0]["model"] == "LR"
    assert result.iloc[1]["model"] == "RF-high"
    assert result.iloc[2]["model"] == "RF-low"


# ---------------------------------------------------------------------------
# _derived_outputs
# ---------------------------------------------------------------------------


def test_derived_outputs_gera_paths_a_partir_do_principal():
    from ml.tools.compare_models import _derived_outputs

    xy, decision = _derived_outputs("charts/comparison.png", None, None)
    assert xy == "charts/comparison_precision_recall.png"
    assert decision == "charts/comparison_decision_map.png"


def test_derived_outputs_sem_output_retorna_none():
    from ml.tools.compare_models import _derived_outputs

    xy, decision = _derived_outputs(None, None, None)
    assert xy is None
    assert decision is None


def test_derived_outputs_respeita_xy_output_explicito():
    from ml.tools.compare_models import _derived_outputs

    xy, _ = _derived_outputs("main.png", "custom_xy.png", None)
    assert xy == "custom_xy.png"


def test_derived_outputs_respeita_decision_output_explicito():
    from ml.tools.compare_models import _derived_outputs

    _, decision = _derived_outputs("main.png", None, "custom_decision.png")
    assert decision == "custom_decision.png"


# ---------------------------------------------------------------------------
# _save_or_show
# ---------------------------------------------------------------------------


def test_save_or_show_salva_quando_output_fornecido():
    from ml.tools.compare_models import _save_or_show

    fig = MagicMock()
    with patch("ml.tools.compare_models.os.makedirs"), patch("ml.tools.compare_models.plt.close"):
        _save_or_show(fig, "output/chart.png")
    fig.savefig.assert_called_once()


def test_save_or_show_chama_plt_show_quando_sem_output():
    from ml.tools.compare_models import _save_or_show

    fig = MagicMock()
    with patch("ml.tools.compare_models.plt.show") as mock_show:
        _save_or_show(fig, None)
    mock_show.assert_called_once()


# ---------------------------------------------------------------------------
# _plot, _plot_precision_recall, _plot_decision_map
# ---------------------------------------------------------------------------


def test_plot_executa_sem_erro():
    from ml.tools.compare_models import _plot

    with patch("ml.tools.compare_models._save_or_show"):
        _plot(_make_df(), None)


def test_plot_precision_recall_executa_sem_erro():
    from ml.tools.compare_models import _plot_precision_recall

    with patch("ml.tools.compare_models._save_or_show"):
        _plot_precision_recall(_make_df(), None)


def test_plot_decision_map_executa_sem_erro():
    from ml.tools.compare_models import _plot_decision_map

    with patch("ml.tools.compare_models._save_or_show"):
        _plot_decision_map(_make_df(), None)


def test_plot_com_um_modelo_nao_falha():
    """Gráfico com um único modelo não deve falhar (sem linha de conexão)."""
    from ml.tools.compare_models import _plot

    with patch("ml.tools.compare_models._save_or_show"):
        _plot(_make_df(n=1), None)


# ---------------------------------------------------------------------------
# _load_best_runs
# ---------------------------------------------------------------------------


def test_load_best_runs_exit_quando_sem_experimentos():
    from ml.tools.compare_models import _load_best_runs

    mock_client = MagicMock()
    mock_client.search_experiments.return_value = []
    with (
        patch("ml.tools.compare_models.mlflow.set_tracking_uri"),
        patch("ml.tools.compare_models.mlflow.tracking.MlflowClient", return_value=mock_client),
        pytest.raises(SystemExit),
    ):
        _load_best_runs("ibm-telco", "telco-churn-2018")


def test_load_best_runs_retorna_dataframe_com_melhor_run():
    from ml.tools.compare_models import _load_best_runs

    mock_exp = MagicMock()
    mock_exp.name = "ibm-telco/telco-churn-2018/random-forest"
    mock_exp.experiment_id = "exp-1"

    mock_run = MagicMock()
    mock_run.data.tags = {"mlflow.runName": "random_forest"}
    mock_run.data.metrics = {
        "f1_mean": 0.72,
        "f1_std": 0.01,
        "roc_auc_mean": 0.88,
        "recall_mean": 0.84,
        "precision_mean": 0.76,
        "train_f1_mean": 0.74,
        "train_roc_auc_mean": 0.90,
    }
    mock_run.info.run_id = "run-abc"

    mock_client = MagicMock()
    mock_client.search_experiments.return_value = [mock_exp]
    mock_client.search_runs.return_value = [mock_run]

    with (
        patch("ml.tools.compare_models.mlflow.set_tracking_uri"),
        patch("ml.tools.compare_models.mlflow.tracking.MlflowClient", return_value=mock_client),
    ):
        df = _load_best_runs("ibm-telco", "telco-churn-2018")

    assert len(df) == 1
    assert df.iloc[0]["model"] == "Random Forest"
    assert df.iloc[0]["f1_mean"] == 0.72


def test_load_best_runs_escolhe_melhor_f1_por_modelo():
    """Dois runs do mesmo modelo — deve reter apenas o de maior F1."""
    from ml.tools.compare_models import _load_best_runs

    mock_exp = MagicMock()
    mock_exp.name = "ibm-telco/proj/rf"
    mock_exp.experiment_id = "exp-1"

    def _run(f1):
        r = MagicMock()
        r.data.tags = {"mlflow.runName": "random_forest"}
        r.data.metrics = {
            "f1_mean": f1,
            "f1_std": 0.0,
            "roc_auc_mean": 0.85,
            "recall_mean": 0.80,
            "precision_mean": 0.75,
            "train_f1_mean": 0.80,
            "train_roc_auc_mean": 0.88,
        }
        r.info.run_id = f"run-{f1}"
        return r

    mock_client = MagicMock()
    mock_client.search_experiments.return_value = [mock_exp]
    mock_client.search_runs.return_value = [_run(0.60), _run(0.75)]

    with (
        patch("ml.tools.compare_models.mlflow.set_tracking_uri"),
        patch("ml.tools.compare_models.mlflow.tracking.MlflowClient", return_value=mock_client),
    ):
        df = _load_best_runs("ibm-telco", "proj")

    assert len(df) == 1
    assert df.iloc[0]["f1_mean"] == 0.75


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_tenant_obrigatorio():
    from ml.tools.compare_models import _parse_args

    with patch.object(sys, "argv", ["compare_models.py", "--tenant", "ibm-telco"]):
        args = _parse_args()
    assert args.tenant == "ibm-telco"
    assert args.project is None
    assert args.output is None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def test_main_chama_os_tres_plots():
    from ml.tools.compare_models import main

    with (
        patch.object(sys, "argv", ["compare_models.py", "--tenant", "ibm-telco"]),
        patch("ml.tools.compare_models._load_best_runs", return_value=_make_df()),
        patch("ml.tools.compare_models._plot") as mock_plot,
        patch("ml.tools.compare_models._plot_precision_recall") as mock_pr,
        patch("ml.tools.compare_models._plot_decision_map") as mock_dm,
    ):
        main()

    mock_plot.assert_called_once()
    mock_pr.assert_called_once()
    mock_dm.assert_called_once()
