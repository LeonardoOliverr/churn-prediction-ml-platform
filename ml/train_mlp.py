"""CLI de treinamento do MLP PyTorch para classificação de churn.

Uso:
    python -m ml.train_mlp --tenant ibm-telco --project telco-churn-2018
    python -m ml.train_mlp --tenant ibm-telco --project telco-churn-2018 \\
        --epochs 150 --lr 0.0005 --dropout 0.4 --patience 20
"""

from __future__ import annotations

import argparse
import time

import mlflow
import mlflow.pytorch
from sklearn.model_selection import train_test_split

from core.logger import get_logger
from ml.config.settings import MLFLOW_TRACKING_URI
from ml.core.registry.db import register_in_db
from ml.data.preprocessing import (
    _build_engine,
    _resolve_project_id,
    _resolve_tenant_id,
    build_preprocessor,
    load_data,
)
from ml.models.mlp.mlp_model import ChurnMLP, evaluate_mlp, make_loaders, train_mlp

logger = get_logger()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Treina MLP PyTorch para churn e registra no MLflow/DB."
    )
    parser.add_argument("--tenant", required=True, help="Slug do tenant.")
    parser.add_argument("--project", required=True, help="Slug do projeto.")
    parser.add_argument("--epochs", type=int, default=100, help="Épocas máximas de treinamento.")
    parser.add_argument("--lr", type=float, default=1e-3, help="Taxa de aprendizado (Adam).")
    parser.add_argument("--dropout", type=float, default=0.3, help="Taxa de dropout entre camadas.")
    parser.add_argument(
        "--patience",
        type=int,
        default=15,
        help="Épocas sem melhora antes de parar (early stopping).",
    )
    parser.add_argument("--batch-size", type=int, default=64, help="Tamanho do mini-batch.")
    parser.add_argument(
        "--pos-weight",
        type=float,
        default=2.7,
        help="Peso da classe positiva (BCEWithLogitsLoss).",
    )
    parser.add_argument(
        "--val-size",
        type=float,
        default=0.2,
        help="Fração do treino reservada para validação.",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5, help="Limiar de decisão para métricas."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula execução sem gravar no banco nem no MLflow.",
    )
    return parser.parse_args()


def _resolve_project_uuid(tenant_slug: str, project_slug: str) -> tuple[str, str]:
    """Retorna (tenant_id, project_id) como strings UUID."""
    engine = _build_engine()
    with engine.connect() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)
    return tenant_id, project_id


def _log_to_mlflow(
    model: ChurnMLP,
    hyperparameters: dict,
    metrics: dict,
    experiment_name: str,
    run_name: str,
) -> str:
    """Loga modelo PyTorch, parâmetros e métricas no MLflow. Retorna run_id."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name) as run:
        flat_params = {f"hyperparameters.{k}": str(v) for k, v in hyperparameters.items()}
        flat_params["model_type"] = "mlp_pytorch"
        mlflow.log_params(flat_params)

        mlflow.log_metrics(
            {
                "f1": metrics["f1_mean"],
                "roc_auc": metrics["roc_auc_mean"],
                "precision": metrics["precision_mean"],
                "recall": metrics["recall_mean"],
                "train_row_count": metrics.get("train_row_count", 0),
                "churn_rate": metrics.get("churn_rate", 0.0),
            }
        )

        mlflow.pytorch.log_model(model, artifact_path="model", registered_model_name=None)

        return run.info.run_id


def main() -> None:
    args = _parse_args()

    experiment_name = f"{args.tenant}/{args.project}/mlp"

    logger.info(
        "mlp_training_started",
        tenant=args.tenant,
        project=args.project,
        epochs=args.epochs,
        lr=args.lr,
        dropout=args.dropout,
        patience=args.patience,
        dry_run=args.dry_run,
    )

    logger.info("data_loading_started")
    X_raw, y = load_data(tenant_slug=args.tenant, project_slug=args.project)
    logger.info("data_loaded", records=len(X_raw), churn_rate=round(float(y.mean()), 4))

    preprocessor = build_preprocessor()
    X_train_raw, X_val_raw, y_train, y_val = train_test_split(
        X_raw, y, test_size=args.val_size, random_state=42, stratify=y
    )

    X_train = preprocessor.fit_transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)

    input_dim = X_train.shape[1]
    train_loader, val_loader = make_loaders(
        X_train, y_train.values, X_val, y_val.values, batch_size=args.batch_size
    )

    model = ChurnMLP(input_dim=input_dim, dropout=args.dropout)
    logger.info("model_created", input_dim=input_dim, architecture=str(model.net))

    t0 = time.time()
    history = train_mlp(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=args.epochs,
        lr=args.lr,
        pos_weight=args.pos_weight,
        patience=args.patience,
    )
    elapsed = round(time.time() - t0, 1)
    epochs_run = len(history["train_loss"])
    logger.info("training_complete", epochs_run=epochs_run, elapsed_seconds=elapsed)

    val_metrics = evaluate_mlp(model, val_loader, threshold=args.threshold)
    logger.info("val_metrics", **val_metrics)

    hyperparameters = {
        "epochs": args.epochs,
        "epochs_run": epochs_run,
        "lr": args.lr,
        "dropout": args.dropout,
        "patience": args.patience,
        "batch_size": args.batch_size,
        "pos_weight": args.pos_weight,
        "val_size": args.val_size,
        "threshold": args.threshold,
        "input_dim": input_dim,
    }

    db_metrics = {
        "f1_mean": val_metrics["f1"],
        "roc_auc_mean": val_metrics["roc_auc"],
        "precision_mean": val_metrics["precision"],
        "recall_mean": val_metrics["recall"],
        "train_row_count": len(X_train_raw),
        "churn_rate": round(float(y.mean()), 4),
    }

    if args.dry_run:
        logger.warning(
            "dry_run_mode",
            message="nenhuma escrita no MLflow ou banco será realizada",
            val_f1=val_metrics["f1"],
            val_roc_auc=val_metrics["roc_auc"],
        )
        return

    run_id = _log_to_mlflow(
        model=model,
        hyperparameters=hyperparameters,
        metrics=db_metrics,
        experiment_name=experiment_name,
        run_name="mlp",
    )
    logger.info("mlflow_logged", run_id=run_id, uri=MLFLOW_TRACKING_URI)

    register_in_db(
        name="mlp-pytorch",
        run_id=run_id,
        metrics=db_metrics,
        tenant_slug=args.tenant,
        project_slug=args.project,
        status="candidate",
        dry_run=False,
        hyperparameters=hyperparameters,
        training_params={"val_size": args.val_size, "threshold": args.threshold},
    )

    logger.info("training_pipeline_complete", run_id=run_id)


if __name__ == "__main__":
    main()
