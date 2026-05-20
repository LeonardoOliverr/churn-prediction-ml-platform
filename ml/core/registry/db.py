"""Database registration for trained models."""

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from core.logger import get_logger
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id

logger = get_logger()


def _next_version(conn, tenant_id, project_id, name: str) -> str:
    """Compute the next semantic version (v1, v2, ...) for a model name within a project."""
    count = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM churn.models
            WHERE tenant_id  = :tenant_id
              AND project_id = :project_id
              AND name = :name
        """
        ),
        {"tenant_id": tenant_id, "project_id": project_id, "name": name},
    ).scalar()
    return f"v{count + 1}"


_INSERT_AUDIT = text("""
    INSERT INTO churn.model_audit_log
        (model_id, tenant_id, project_id, action, old_status, new_status, changed_by, metrics_snapshot)
    VALUES
        (:model_id, :tenant_id, :project_id, :action, :old_status, :new_status, :changed_by, :metrics_snapshot)
""")


def register_in_db(
    name: str,
    run_id: str,
    metrics: dict,
    tenant_slug: str | None,
    project_slug: str | None,
    status: str,
    dry_run: bool,
    hyperparameters: dict | None = None,
    training_params: dict | None = None,
) -> None:
    """Insert the trained model metadata into churn.models and audit log."""
    hyperparameters = hyperparameters or {}
    training_params = training_params or {}
    engine = _build_engine()
    with engine.begin() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug) if tenant_slug else None
        project_id = _resolve_project_id(conn, tenant_id, project_slug) if project_slug else None
        version = _next_version(conn, tenant_id, project_id, name)

    if dry_run:
        logger.warning(
            "db_registration_skipped",
            reason="dry_run",
            name=name,
            version=version,
            status=status,
            tenant=tenant_slug or "-",
            project=project_slug or "-",
            mlflow_run_id=run_id,
            f1=round(metrics["f1_mean"], 4),
            roc_auc=round(metrics["roc_auc_mean"], 4),
            precision=round(metrics["precision_mean"], 4),
            recall=round(metrics["recall_mean"], 4),
            hyperparameters=hyperparameters,
            training_params=training_params,
        )
        return

    metrics_snapshot = {
        "f1": round(metrics["f1_mean"], 4),
        "roc_auc": round(metrics["roc_auc_mean"], 4),
        "recall": round(metrics["recall_mean"], 4),
        "precision": round(metrics["precision_mean"], 4),
    }

    with engine.begin() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug) if tenant_slug else None
        project_id = _resolve_project_id(conn, tenant_id, project_slug) if project_slug else None

        row = conn.execute(
            text(
                """
                INSERT INTO churn.models
                    (name, version, tenant_id, project_id,
                     mlflow_run_id, f1_score, roc_auc, precision_score, recall_score,
                     status, hyperparameters, training_params,
                     training_row_count, training_churn_rate, tags)
                VALUES
                    (:name, :version, :tenant_id, :project_id,
                     :run_id, :f1, :roc_auc, :precision, :recall,
                     :status, :hyperparameters, :training_params,
                     :training_row_count, :training_churn_rate, :tags)
                RETURNING id
            """
            ).bindparams(
                bindparam("hyperparameters", type_=JSONB),
                bindparam("training_params", type_=JSONB),
            ),
            {
                "name": name,
                "version": version,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "run_id": run_id,
                "f1": round(metrics["f1_mean"], 4),
                "roc_auc": round(metrics["roc_auc_mean"], 4),
                "precision": round(metrics["precision_mean"], 4),
                "recall": round(metrics["recall_mean"], 4),
                "status": status,
                "hyperparameters": hyperparameters,
                "training_params": training_params,
                "training_row_count": metrics.get("train_row_count"),
                "training_churn_rate": metrics.get("churn_rate"),
                "tags": [],
            },
        ).mappings().first()

        model_id = str(row["id"])

        conn.execute(
            _INSERT_AUDIT.bindparams(bindparam("metrics_snapshot", type_=JSONB)),
            {
                "model_id": model_id,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "action": "registered",
                "old_status": None,
                "new_status": status,
                "changed_by": "ml.train",
                "metrics_snapshot": metrics_snapshot,
            },
        )

    logger.info(
        "model_registered",
        name=name,
        version=version,
        status=status,
        model_id=model_id,
        tenant=tenant_slug or "-",
        project=project_slug or "-",
    )
