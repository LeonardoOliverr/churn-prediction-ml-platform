"""
Treina e avalia DummyClassifier e Logistic Regression como baselines.
Loga métricas no MLflow e registra todos os modelos em churn.models com status.

Uso:
    # escopo global (todos os tenants)
    python ml/baseline.py
    python ml/baseline.py --dry-run

    # escopo tenant
    python ml/baseline.py --tenant <tenant-slug>
    python ml/baseline.py --tenant <tenant-slug> --dry-run

    # escopo project
    python ml/baseline.py --tenant <tenant-slug> --project <project-slug>
    python ml/baseline.py --tenant <tenant-slug> --project <project-slug> --dry-run
"""

import argparse
import os
import sys

import mlflow
import mlflow.sklearn
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(__file__))
from config import MLFLOW_TRACKING_URI
from preprocessing import (
    _build_engine,
    _resolve_project_id,
    _resolve_tenant_id,
    build_preprocessor,
    load_data,
)

CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

SCORING = ["f1", "roc_auc", "recall", "precision"]

MODELS = {
    "dummy_stratified": DummyClassifier(strategy="stratified", random_state=42),
    "logistic_regression": LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
    ),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Treina e registra o baseline de churn.")
    parser.add_argument("--tenant",  default=None, help="Slug do tenant. Omitir para escopo global.")
    parser.add_argument("--project", default=None, help="Slug do projeto. Requer --tenant.")
    parser.add_argument("--dry-run", action="store_true", help="Simula execução sem gravar no banco nem no MLflow.")
    args = parser.parse_args()

    if args.project and not args.tenant:
        parser.error("--project requer --tenant.")

    return args


def _derive_scope(tenant_slug: str | None, project_slug: str | None) -> tuple[str, str, str]:
    """Retorna (scope, experiment_name, model_name) a partir dos slugs."""
    if tenant_slug is None:
        return "global", "global/baseline", "global-baseline"
    if project_slug is None:
        return "tenant", f"{tenant_slug}/baseline", f"{tenant_slug}-baseline"
    return "project", f"{tenant_slug}/{project_slug}/baseline", f"{tenant_slug}-{project_slug}-baseline"


def _cv_metrics(pipeline: Pipeline, X, y) -> dict[str, float]:
    """Executa cross-validation e retorna métricas agregadas (mean + std)."""
    results = cross_validate(pipeline, X, y, cv=CV, scoring=SCORING)
    metrics = {}
    for metric in SCORING:
        scores = results[f"test_{metric}"]
        metrics[f"{metric}_mean"] = float(np.mean(scores))
        metrics[f"{metric}_std"]  = float(np.std(scores))
    return metrics


def _run_model(name: str, model, X, y, dry_run: bool) -> tuple[str, dict]:
    """Treina, avalia, salva o artefato no MLflow e retorna (run_id, metrics)."""
    pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", model),
    ])

    print(f"\n[{name}] Executando cross-validation ({CV.n_splits} folds)...")
    metrics = _cv_metrics(pipeline, X, y)

    print(f"  F1        : {metrics['f1_mean']:.4f} ± {metrics['f1_std']:.4f}")
    print(f"  ROC-AUC   : {metrics['roc_auc_mean']:.4f} ± {metrics['roc_auc_std']:.4f}")
    print(f"  Recall    : {metrics['recall_mean']:.4f}")
    print(f"  Precision : {metrics['precision_mean']:.4f}")

    if dry_run:
        print(f"  [dry-run] MLflow run NÃO criado.")
        return "dry-run-run-id", metrics

    with mlflow.start_run(run_name=name) as run:
        mlflow.log_params({
            "model_type":   name,
            "cv_folds":     CV.n_splits,
            "cv_strategy":  "StratifiedKFold",
            "class_weight": getattr(model, "class_weight", "none"),
        })
        mlflow.log_metrics(metrics)

        # Treina o pipeline final em todos os dados para uso em inferência.
        pipeline.fit(X, y)
        mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="model",
        )

        run_id = run.info.run_id

    return run_id, metrics


def _next_version(conn, scope: str, tenant_id, project_id, name: str) -> str:
    """Calcula a próxima versão (v1, v2, ...) para o modelo no escopo dado."""
    count = conn.execute(
        text("""
            SELECT COUNT(*) FROM churn.models
            WHERE scope = :scope
              AND (tenant_id  IS NOT DISTINCT FROM :tenant_id)
              AND (project_id IS NOT DISTINCT FROM :project_id)
              AND name = :name
        """),
        {"scope": scope, "tenant_id": tenant_id, "project_id": project_id, "name": name},
    ).scalar()
    return f"v{count + 1}"


def _register_in_db(
    name: str,
    run_id: str,
    metrics: dict,
    scope: str,
    tenant_slug: str | None,
    project_slug: str | None,
    status: str,
    dry_run: bool,
) -> None:
    """Insere o modelo em churn.models. Se status='active', arquiva o active anterior."""
    engine = _build_engine()
    with engine.begin() as conn:
        tenant_id  = _resolve_tenant_id(conn, tenant_slug)                     if tenant_slug  else None
        project_id = _resolve_project_id(conn, tenant_id, project_slug)        if project_slug else None
        version    = _next_version(conn, scope, tenant_id, project_id, name)

    if dry_run:
        print(f"\n[dry-run] Registro que seria gravado em churn.models:")
        print(f"  name          : {name}")
        print(f"  version       : {version}")
        print(f"  status        : {status}")
        print(f"  scope         : {scope}")
        print(f"  tenant        : {tenant_slug or '—'}")
        print(f"  project       : {project_slug or '—'}")
        print(f"  mlflow_run_id : {run_id}")
        print(f"  f1_score      : {round(metrics['f1_mean'], 4)}")
        print(f"  roc_auc       : {round(metrics['roc_auc_mean'], 4)}")
        print(f"  precision     : {round(metrics['precision_mean'], 4)}")
        print(f"  recall        : {round(metrics['recall_mean'], 4)}")
        print(f"[dry-run] Nenhuma escrita realizada.")
        return

    with engine.begin() as conn:
        tenant_id  = _resolve_tenant_id(conn, tenant_slug)                     if tenant_slug  else None
        project_id = _resolve_project_id(conn, tenant_id, project_slug)        if project_slug else None

        if status == "active":
            conn.execute(
                text("""
                    UPDATE churn.models SET status = 'archived'
                    WHERE scope = :scope
                      AND (tenant_id  IS NOT DISTINCT FROM :tenant_id)
                      AND (project_id IS NOT DISTINCT FROM :project_id)
                      AND name = :name
                      AND status = 'active'
                """),
                {"scope": scope, "tenant_id": tenant_id, "project_id": project_id, "name": name},
            )

        conn.execute(
            text("""
                INSERT INTO churn.models
                    (name, version, scope, tenant_id, project_id,
                     mlflow_run_id, f1_score, roc_auc, precision_score, recall_score, status)
                VALUES
                    (:name, :version, :scope, :tenant_id, :project_id,
                     :run_id, :f1, :roc_auc, :precision, :recall, :status)
            """),
            {
                "name":       name,
                "version":    version,
                "scope":      scope,
                "tenant_id":  tenant_id,
                "project_id": project_id,
                "run_id":     run_id,
                "f1":         round(metrics["f1_mean"], 4),
                "roc_auc":    round(metrics["roc_auc_mean"], 4),
                "precision":  round(metrics["precision_mean"], 4),
                "recall":     round(metrics["recall_mean"], 4),
                "status":     status,
            },
        )

    label = f"tenant={tenant_slug}" if tenant_slug else "global"
    print(f"  Registrado: {name} {version} | status={status} | scope={scope} | {label}")


def main() -> None:
    args = _parse_args()
    scope, experiment_name, _ = _derive_scope(args.tenant, args.project)

    if args.dry_run:
        print("=" * 50)
        print("MODO DRY-RUN — nenhuma escrita será realizada")
        print("=" * 50)

    print(f"\nEscopo      : {scope}")
    print(f"Tenant      : {args.tenant or '—'}")
    print(f"Projeto     : {args.project or '—'}")
    print(f"Experimento : {experiment_name}")

    if not args.dry_run:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(experiment_name)

    print("\nCarregando dados do PostgreSQL...")
    X, y = load_data(tenant_slug=args.tenant, project_slug=args.project)
    print(f"  {len(X)} registros | churn rate: {y.mean():.1%}")

    results: list[tuple[str, str, dict]] = []
    for name, model in MODELS.items():
        run_id, metrics = _run_model(name, model, X, y, dry_run=args.dry_run)
        results.append((name, run_id, metrics))

    best_name = max(results, key=lambda t: t[2]["f1_mean"])[0]

    print(f"\n{'='*50}")
    print(f"Melhor modelo : {best_name}")
    best_metrics = next(m for n, _, m in results if n == best_name)
    print(f"F1 médio      : {best_metrics['f1_mean']:.4f}")
    print(f"ROC-AUC médio : {best_metrics['roc_auc_mean']:.4f}")
    print(f"{'='*50}")

    for name, run_id, metrics in results:
        status = "active" if name == best_name else "shadow"
        _register_in_db(
            name=name,
            run_id=run_id,
            metrics=metrics,
            scope=scope,
            tenant_slug=args.tenant,
            project_slug=args.project,
            status=status,
            dry_run=args.dry_run,
        )

    if not args.dry_run:
        print(f"\nResultados no MLflow: {MLFLOW_TRACKING_URI}")


if __name__ == "__main__":
    main()
