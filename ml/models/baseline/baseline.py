"""
Treina e avalia DummyClassifier e Logistic Regression como baselines.
Loga métricas no MLflow e registra todos os modelos em churn.models com status técnico.

Uso:
    # escopo global (todos os tenants)
    python ml/models/baseline/baseline.py
    python ml/models/baseline/baseline.py --dry-run

    # escopo tenant
    python ml/models/baseline/baseline.py --tenant <tenant-slug>
    python ml/models/baseline/baseline.py --tenant <tenant-slug> --dry-run

    # escopo project
    python ml/models/baseline/baseline.py --tenant <tenant-slug> --project <project-slug>
    python ml/models/baseline/baseline.py --tenant <tenant-slug> --project <project-slug> --dry-run
"""

import argparse
import os
import sys

import joblib
import tempfile

import mlflow
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sqlalchemy import text

# Raiz do projeto no path para imports absolutos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from ml.core.config import MLFLOW_TRACKING_URI
from ml.core.preprocessing import (
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
    """Executa cross-validation e retorna métricas de teste e treino por fold.

    Retorna mean/std das métricas de teste (validação) e mean das métricas de treino.
    A diferença train_mean − test_mean indica overfitting: gap > 0.10 é sinal de alerta.
    """
    results = cross_validate(pipeline, X, y, cv=CV, scoring=SCORING, return_train_score=True)
    metrics = {}
    for metric in SCORING:
        test_scores  = results[f"test_{metric}"]
        train_scores = results[f"train_{metric}"]
        metrics[f"{metric}_mean"]       = float(np.mean(test_scores))
        metrics[f"{metric}_std"]        = float(np.std(test_scores))
        metrics[f"train_{metric}_mean"] = float(np.mean(train_scores))
    return metrics


def _run_model(name: str, model, X, y, dry_run: bool) -> tuple[str, dict]:
    """Treina, avalia, salva o artefato no MLflow e retorna (run_id, metrics)."""
    pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", model),
    ])

    print(f"\n[{name}] Executando cross-validation ({CV.n_splits} folds)...")
    metrics = _cv_metrics(pipeline, X, y)

    f1_gap      = metrics["train_f1_mean"] - metrics["f1_mean"]
    roc_gap     = metrics["train_roc_auc_mean"] - metrics["roc_auc_mean"]
    gap_warning = "  ⚠ overfitting" if f1_gap > 0.10 else ""

    print(f"  F1        : treino={metrics['train_f1_mean']:.4f}  teste={metrics['f1_mean']:.4f} ± {metrics['f1_std']:.4f}  gap={f1_gap:+.4f}{gap_warning}")
    print(f"  ROC-AUC   : treino={metrics['train_roc_auc_mean']:.4f}  teste={metrics['roc_auc_mean']:.4f} ± {metrics['roc_auc_std']:.4f}  gap={roc_gap:+.4f}")
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
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.pkl")
            joblib.dump(pipeline, model_path)
            mlflow.log_artifact(model_path, artifact_path="model")

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
    """Insere o modelo em churn.models com status técnico."""
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

    if args.tenant is None:
        scope_prefix = "global"
    elif args.project is None:
        scope_prefix = args.tenant
    else:
        scope_prefix = f"{args.tenant}-{args.project}"

    for name, run_id, metrics in results:
        db_name = f"{scope_prefix}-{name.replace('_', '-')}"
        status = "approved" if name == best_name else "trained"
        _register_in_db(
            name=db_name,
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
