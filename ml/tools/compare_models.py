"""
Gera gráficos comparativos dos modelos treinados no MLflow.
Consulta os experimentos do escopo informado e compara F1, ROC-AUC, Recall,
Precision, gap treino/teste e mapas estratégicos de decisão.

Uso:
    # escopo tenant — todos os projetos do tenant
    python ml/tools/compare_models.py --tenant ibm-telco

    # escopo project — só os modelos daquele projeto
    python ml/tools/compare_models.py --tenant ibm-telco --project telco-churn-2018

    # salvar PNGs
    python ml/tools/compare_models.py --tenant ibm-telco --project telco-churn-2018 --output charts/model_comparison.png
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import mlflow

from ml.config.settings import MLFLOW_TRACKING_URI


METRICS = ["f1_mean", "roc_auc_mean", "recall_mean", "precision_mean"]
METRIC_LABELS = {
    "f1_mean":        "F1",
    "roc_auc_mean":   "ROC-AUC",
    "recall_mean":    "Recall",
    "precision_mean": "Precision",
}
THRESHOLDS = {
    "f1_mean":      0.68,
    "roc_auc_mean": 0.88,
    "recall_mean":  0.82,
}
MODEL_ORDER = {
    "Dummy Stratified": 1,
    "Dummyclassifier": 1,
    "Logistic Regression": 2,
    "Random Forest": 3,
    "Xgboost": 4,
    "Lightgbm": 5,
    "Logreg Fe": 6,
    "Mlp": 7,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compara modelos treinados no MLflow.")
    parser.add_argument("--tenant", required=True, help="Slug do tenant.")
    parser.add_argument("--project", default=None, help="Slug do projeto. Omitir para ver todos os projetos do tenant.")
    parser.add_argument("--output", default=None, help="Caminho para salvar o PNG principal. Se omitido, exibe na tela.")
    parser.add_argument("--xy-output", default=None, help="Caminho para salvar o gráfico Precision x Recall.")
    parser.add_argument("--decision-output", default=None, help="Caminho para salvar o mapa de decisão F1 x ROC-AUC.")
    return parser.parse_args()


def _model_label(run, experiment_name: str) -> str:
    """Define o nome visível do modelo a partir do run_name do MLflow."""
    run_name = run.data.tags.get("mlflow.runName") or experiment_name.rsplit("/", 1)[-1]
    return run_name.replace("_", " ").replace("-", " ").title()


def _load_best_runs(tenant: str, project: str | None) -> pd.DataFrame:
    """Busca o melhor run (maior F1) de cada modelo no escopo informado."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()

    prefix = f"{tenant}/{project}/" if project else f"{tenant}/"
    experiments = [e for e in client.search_experiments() if e.name.startswith(prefix)]

    if not experiments:
        print(f"Nenhum experimento encontrado para {prefix}*")
        sys.exit(1)

    rows = []
    for experiment in experiments:
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="",
            order_by=["metrics.f1_mean DESC"],
            max_results=100,
        )

        best_by_model = {}
        for run in runs:
            model_name = _model_label(run, experiment.name)
            run_f1 = run.data.metrics.get("f1_mean", float("-inf"))
            current = best_by_model.get(model_name)
            current_f1 = current.data.metrics.get("f1_mean", float("-inf")) if current else float("-inf")

            if current is None or run_f1 > current_f1:
                best_by_model[model_name] = run

        for model_name, run in best_by_model.items():
            metrics = run.data.metrics
            rows.append({
                "model":              model_name,
                "order":              MODEL_ORDER.get(model_name, 99),
                "experiment":         experiment.name,
                "run_id":             run.info.run_id,
                "f1_mean":            metrics.get("f1_mean", float("nan")),
                "f1_std":             metrics.get("f1_std", 0.0),
                "roc_auc_mean":       metrics.get("roc_auc_mean", float("nan")),
                "recall_mean":        metrics.get("recall_mean", float("nan")),
                "precision_mean":     metrics.get("precision_mean", float("nan")),
                "train_f1_mean":      metrics.get("train_f1_mean", float("nan")),
                "train_roc_auc_mean": metrics.get("train_roc_auc_mean", float("nan")),
            })

    return _line_df(pd.DataFrame(rows))


def _line_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena os modelos na sequência de evolução para gráficos com linha."""
    return df.sort_values(["order", "f1_mean"], ascending=[True, False]).reset_index(drop=True)


def _derived_outputs(output: str | None, xy_output: str | None, decision_output: str | None) -> tuple[str | None, str | None]:
    """Define os nomes dos gráficos extras a partir do PNG principal."""
    if not output:
        return xy_output, decision_output

    root, ext = os.path.splitext(output)
    ext = ext or ".png"
    return (
        xy_output or f"{root}_precision_recall{ext}",
        decision_output or f"{root}_decision_map{ext}",
    )


def _save_or_show(fig, output: str | None) -> None:
    """Salva o gráfico quando output foi informado; caso contrário, exibe na tela."""
    if output:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        fig.savefig(output, dpi=150, bbox_inches="tight")
        print(f"Gráfico salvo em: {output}")
        plt.close(fig)
        return

    plt.show()


def _plot(df: pd.DataFrame, output: str | None) -> None:
    """Gera o painel principal de comparação de métricas."""
    df = _line_df(df)
    n_models = len(df)
    x = np.arange(n_models)
    labels = df["model"].tolist()

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    scope_label = f"{df['experiment'].iloc[0].rsplit('/', 1)[0]}" if len(df) else ""
    fig.suptitle(f"Comparação de Modelos — {scope_label}", fontsize=14, fontweight="bold")

    ax = axes[0]
    width = 0.2
    offsets = [-1.5, -0.5, 0.5, 1.5]
    bar_colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]

    for metric, offset, color in zip(METRICS, offsets, bar_colors):
        values = df[metric].tolist()
        bars = ax.bar(x + offset * width, values, width, label=METRIC_LABELS[metric], color=color, alpha=0.85)
        for bar, value in zip(bars, values):
            if not np.isnan(value):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.005,
                    f"{value:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )

    for metric, color in [("f1_mean", "#4C72B0"), ("roc_auc_mean", "#55A868"), ("recall_mean", "#C44E52")]:
        ax.axhline(THRESHOLDS[metric], color=color, linestyle="--", linewidth=0.8, alpha=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.set_title("Métricas por Modelo")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    test_f1 = df["f1_mean"].tolist()
    train_f1 = df["train_f1_mean"].tolist()

    ax.bar(x - 0.2, train_f1, 0.4, label="Treino", color="#E8A838", alpha=0.85)
    ax.bar(x + 0.2, test_f1, 0.4, label="Teste", color="#4C72B0", alpha=0.85)

    for index, (train_value, test_value) in enumerate(zip(train_f1, test_f1)):
        if not np.isnan(train_value) and not np.isnan(test_value):
            gap = train_value - test_value
            color = "#C44E52" if gap > 0.10 else "#55A868"
            ax.text(index, max(train_value, test_value) + 0.015, f"gap={gap:+.2f}", ha="center", fontsize=8, color=color, fontweight="bold")

    ax.axhline(0.10, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("F1")
    ax.set_title("Overfitting — F1 Treino vs Teste")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[2]
    ax.axis("off")

    table_data = []
    for _, row in df.iterrows():
        f1 = row["f1_mean"]
        roc_auc = row["roc_auc_mean"]
        recall = row["recall_mean"]
        approved = (
            (not np.isnan(f1) and f1 > THRESHOLDS["f1_mean"])
            and (not np.isnan(roc_auc) and roc_auc > THRESHOLDS["roc_auc_mean"])
            and (not np.isnan(recall) and recall > THRESHOLDS["recall_mean"])
        )
        table_data.append([
            row["model"],
            f"{f1:.4f}" if not np.isnan(f1) else "—",
            f"{roc_auc:.4f}" if not np.isnan(roc_auc) else "—",
            f"{recall:.4f}" if not np.isnan(recall) else "—",
            "✅ Sim" if approved else "❌ Não",
        ])

    table = ax.table(
        cellText=table_data,
        colLabels=["Modelo", "F1", "ROC-AUC", "Recall", "Promove?"],
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 2.0)

    threshold_note = (
        f"Critérios: F1 > {THRESHOLDS['f1_mean']:.2f}  |  "
        f"ROC-AUC > {THRESHOLDS['roc_auc_mean']:.2f}  |  "
        f"Recall > {THRESHOLDS['recall_mean']:.2f}"
    )
    ax.set_title(f"Decisão\n{threshold_note}", fontsize=9)

    plt.tight_layout()
    _save_or_show(fig, output)


def _plot_precision_recall(df: pd.DataFrame, output: str | None) -> None:
    """Gera gráfico XY de Precision x Recall para visualizar tradeoff de retenção."""
    plot_df = _line_df(df)
    fig, ax = plt.subplots(figsize=(9, 6))

    x = plot_df["recall_mean"].to_numpy()
    y = plot_df["precision_mean"].to_numpy()
    f1 = plot_df["f1_mean"].to_numpy()

    ax.plot(x, y, color="#444444", linewidth=1.4, alpha=0.65, zorder=1)
    scatter = ax.scatter(
        x,
        y,
        c=f1,
        s=260,
        cmap="viridis",
        edgecolor="white",
        linewidth=1.4,
        zorder=2,
    )

    for _, row in plot_df.iterrows():
        ax.annotate(
            f"{row['model']}\nF1={row['f1_mean']:.4f}",
            (row["recall_mean"], row["precision_mean"]),
            textcoords="offset points",
            xytext=(9, 8),
            fontsize=8,
        )

    ax.axvline(THRESHOLDS["recall_mean"], color="#C44E52", linestyle="--", linewidth=1.0, alpha=0.75)
    ax.set_title("Tradeoff Precision x Recall")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(max(0, np.nanmin(x) - 0.08), min(1, np.nanmax(x) + 0.08))
    ax.set_ylim(max(0, np.nanmin(y) - 0.08), min(1, np.nanmax(y) + 0.08))
    ax.grid(alpha=0.25)

    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("F1")

    plt.tight_layout()
    _save_or_show(fig, output)


def _plot_decision_map(df: pd.DataFrame, output: str | None) -> None:
    """Gera mapa F1 x ROC-AUC com zona de promoção do modelo."""
    plot_df = _line_df(df)
    fig, ax = plt.subplots(figsize=(9, 6))

    x = plot_df["roc_auc_mean"].to_numpy()
    y = plot_df["f1_mean"].to_numpy()
    recall = plot_df["recall_mean"].to_numpy()

    ax.axvline(THRESHOLDS["roc_auc_mean"], color="#55A868", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.axhline(THRESHOLDS["f1_mean"], color="#4C72B0", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.fill_between(
        [THRESHOLDS["roc_auc_mean"], 1],
        THRESHOLDS["f1_mean"],
        1,
        color="#55A868",
        alpha=0.08,
        label="Zona de promoção",
    )

    sizes = 120 + np.nan_to_num(recall, nan=0.0) * 240
    scatter = ax.scatter(
        x,
        y,
        c=recall,
        s=sizes,
        cmap="plasma",
        edgecolor="white",
        linewidth=1.4,
        zorder=2,
    )
    ax.plot(x, y, color="#444444", linewidth=1.2, alpha=0.45, zorder=1)

    for _, row in plot_df.iterrows():
        ax.annotate(
            row["model"],
            (row["roc_auc_mean"], row["f1_mean"]),
            textcoords="offset points",
            xytext=(9, 8),
            fontsize=8,
        )

    ax.set_title("Mapa de Decisão F1 x ROC-AUC")
    ax.set_xlabel("ROC-AUC")
    ax.set_ylabel("F1")
    ax.set_xlim(max(0, np.nanmin(x) - 0.06), min(1, np.nanmax(x) + 0.06))
    ax.set_ylim(max(0, np.nanmin(y) - 0.08), min(1, np.nanmax(y) + 0.08))
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right")

    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Recall")

    plt.tight_layout()
    _save_or_show(fig, output)


def main() -> None:
    args = _parse_args()
    scope = f"{args.tenant}/{args.project}" if args.project else args.tenant
    print(f"Carregando experimentos de {scope}/...")
    df = _load_best_runs(args.tenant, args.project)
    xy_output, decision_output = _derived_outputs(args.output, args.xy_output, args.decision_output)

    print(f"\n{len(df)} modelo(s) encontrado(s):\n")
    print(df[["model", "f1_mean", "roc_auc_mean", "recall_mean", "precision_mean", "train_f1_mean"]].to_string(index=False))

    _plot(df, args.output)
    _plot_precision_recall(df, xy_output)
    _plot_decision_map(df, decision_output)


if __name__ == "__main__":
    main()
