"""CLI unificado de treinamento.

Uso:
    python -m ml.train --model baseline [--tenant X] [--project Y] [--dry-run]
    python -m ml.train --model random_forest [--n-estimators 300] [--max-depth 10]
    python -m ml.train --model random_forest --holdout-size 0.0
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from ml.config.settings import MLFLOW_TRACKING_URI
from ml.core.training.metrics import CV
from ml.evaluation import CandidateResult, build_run_report, compare_results

if TYPE_CHECKING:
    from ml.core.model_spec import ModelSpec


class _MlflowProxy:
    """Proxy leve para manter o import do CLI sem exigir mlflow instalado."""

    def set_tracking_uri(self, *args, **kwargs):
        import mlflow as real_mlflow

        return real_mlflow.set_tracking_uri(*args, **kwargs)

    def set_experiment(self, *args, **kwargs):
        import mlflow as real_mlflow

        return real_mlflow.set_experiment(*args, **kwargs)


mlflow = _MlflowProxy()


def load_data(*args, **kwargs):
    from ml.data.preprocessing import load_data as real_load_data

    return real_load_data(*args, **kwargs)


def train_with_cv(*args, **kwargs):
    from ml.core.training.train import train_with_cv as real_train_with_cv

    return real_train_with_cv(*args, **kwargs)


def log_to_mlflow(*args, **kwargs):
    from ml.core.registry.mlflow import log_to_mlflow as real_log_to_mlflow

    return real_log_to_mlflow(*args, **kwargs)


def register_in_db(*args, **kwargs):
    from ml.core.registry.db import register_in_db as real_register_in_db

    return real_register_in_db(*args, **kwargs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Treina e registra modelos de churn.")
    parser.add_argument(
        "--model",
        required=True,
        choices=["baseline", "random_forest"],
        help="Familia de modelos a treinar.",
    )
    parser.add_argument(
        "--tenant",
        default=None,
        help="Slug do tenant. Omitir para escopo global.",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Slug do projeto. Requer --tenant.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula execucao sem gravar no banco nem no MLflow.",
    )
    parser.add_argument(
        "--holdout-size",
        type=float,
        default=0.2,
        help="Fracao do dataset reservada para holdout final (0.0 = CV puro).",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=500,
        help="Numero de arvores no Random Forest.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Profundidade maxima das arvores.",
    )
    args = parser.parse_args()

    if args.project and not args.tenant:
        parser.error("--project requer --tenant.")

    return args


def _resolve_specs(model_name: str) -> list[ModelSpec]:
    """Retorna a lista de ModelSpec para o modelo solicitado."""
    from ml.models import BASELINE_SPECS, RANDOM_FOREST_SPECS

    if model_name == "baseline":
        return BASELINE_SPECS
    if model_name == "random_forest":
        return RANDOM_FOREST_SPECS
    raise ValueError(f"Modelo desconhecido: {model_name!r}")


def _derive_scope(
    tenant_slug: str | None,
    project_slug: str | None,
    experiment_suffix: str,
) -> tuple[str, str]:
    """Retorna (scope, experiment_name) a partir dos slugs e do sufixo."""
    if tenant_slug is None:
        return "global", f"global/{experiment_suffix}"
    if project_slug is None:
        return "tenant", f"{tenant_slug}/{experiment_suffix}"
    return "project", f"{tenant_slug}/{project_slug}/{experiment_suffix}"


def _db_name(
    scope: str,
    tenant_slug: str | None,
    project_slug: str | None,
    spec_name: str,
) -> str:
    """Gera o nome do modelo para registro em churn.models."""
    display = spec_name.replace("_", "-")
    if scope == "global":
        return f"global-{display}"
    if scope == "tenant":
        return f"{tenant_slug}-{display}"
    return f"{tenant_slug}-{project_slug}-{display}"


def _build_hyperparameters(spec: ModelSpec, hp_overrides: dict[str, Any]) -> dict[str, Any]:
    """Retorna os hiperparametros finais usados para instanciar o estimador."""
    return {**spec.default_params, **hp_overrides, **spec.fixed_params}


def _build_training_params(holdout_size: float) -> dict[str, Any]:
    """Retorna os parametros do processo de treino."""
    return {
        "cv_folds": CV.n_splits,
        "cv_strategy": type(CV).__name__,
        "holdout_size": holdout_size,
        "primary_metric": "f1",
    }


def _mlflow_param_value(value: Any) -> str:
    """Normaliza valores para o contrato string de parametros do MLflow."""
    return "None" if value is None else str(value)


def _build_mlflow_params(
    spec: ModelSpec,
    hyperparameters: dict[str, Any],
    training_params: dict[str, Any],
) -> dict[str, str]:
    """Constroi o dict flat de parametros a logar no MLflow."""
    params = {"model_type": spec.name}
    params.update(
        {
            f"hyperparameters.{key}": _mlflow_param_value(value)
            for key, value in hyperparameters.items()
        }
    )
    params.update(
        {
            f"training_params.{key}": _mlflow_param_value(value)
            for key, value in training_params.items()
        }
    )
    return params


def _hp_overrides_from_args(args: argparse.Namespace) -> dict:
    """Extrai hiperparametros opcionais do CLI."""
    hp_overrides: dict = {}
    if args.n_estimators != 500:
        hp_overrides["n_estimators"] = args.n_estimators
    if args.max_depth is not None:
        hp_overrides["max_depth"] = args.max_depth
    return hp_overrides


def _print_run_context(
    scope: str,
    tenant_slug: str | None,
    project_slug: str | None,
    experiment_name: str,
    holdout_size: float,
) -> None:
    print(f"\nEscopo      : {scope}")
    print(f"Tenant      : {tenant_slug or '-'}")
    print(f"Projeto     : {project_slug or '-'}")
    print(f"Experimento : {experiment_name}")
    if holdout_size > 0:
        print(f"Holdout     : {holdout_size:.0%} reservado para avaliacao final")
    else:
        print("Holdout     : desativado (CV puro)")


def _train_candidates(
    specs: list[ModelSpec],
    X,
    y,
    args: argparse.Namespace,
    hp_overrides: dict,
) -> list[CandidateResult]:
    """Executa treino e logging, retornando candidatos avaliaveis pelo run."""
    candidates: list[CandidateResult] = []
    for spec in specs:
        applicable = {k: v for k, v in hp_overrides.items() if k in spec.cli_overrides}
        hyperparameters = _build_hyperparameters(spec, applicable)
        training_params = _build_training_params(args.holdout_size)
        result = train_with_cv(
            spec,
            X,
            y,
            hp_overrides=applicable,
            holdout_size=args.holdout_size,
        )
        pipeline = result["pipeline"]
        metrics = result["metrics"]

        if args.dry_run:
            print("  [dry-run] MLflow run NAO criado.")
            run_id = "dry-run-run-id"
        else:
            params = _build_mlflow_params(spec, hyperparameters, training_params)
            run_id = log_to_mlflow(
                run_name=spec.name,
                params=params,
                metrics=metrics,
                pipeline=pipeline,
                log_feature_importances=spec.log_feature_importances,
            )

        candidates.append(
            CandidateResult(
                spec=spec,
                run_id=run_id,
                metrics=metrics,
                hyperparameters=hyperparameters,
                training_params=training_params,
            )
        )

    return candidates


def _register_comparison(
    comparison,
    scope: str,
    tenant_slug: str | None,
    project_slug: str | None,
    dry_run: bool,
) -> None:
    """Registra todos os candidatos com o status decidido pela comparacao."""
    for candidate in comparison.candidates:
        db_name = _db_name(scope, tenant_slug, project_slug, candidate.spec.name)
        register_in_db(
            name=db_name,
            run_id=candidate.run_id,
            metrics=candidate.metrics,
            scope=scope,
            tenant_slug=tenant_slug,
            project_slug=project_slug,
            status=comparison.status_by_model[candidate.spec.name],
            dry_run=dry_run,
            hyperparameters=candidate.hyperparameters,
            training_params=candidate.training_params,
        )


def main() -> None:
    args = _parse_args()
    specs = _resolve_specs(args.model)
    experiment_suffix = specs[0].experiment_suffix
    scope, experiment_name = _derive_scope(args.tenant, args.project, experiment_suffix)

    if args.dry_run:
        print("=" * 50)
        print("MODO DRY-RUN - nenhuma escrita sera realizada")
        print("=" * 50)

    _print_run_context(
        scope=scope,
        tenant_slug=args.tenant,
        project_slug=args.project,
        experiment_name=experiment_name,
        holdout_size=args.holdout_size,
    )

    if not args.dry_run:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(experiment_name)

    print("\nCarregando dados do PostgreSQL...")
    X, y = load_data(tenant_slug=args.tenant, project_slug=args.project)
    print(f"  {len(X)} registros | churn rate: {y.mean():.1%}")

    hp_overrides = _hp_overrides_from_args(args)
    candidates = _train_candidates(specs, X, y, args, hp_overrides)
    comparison = compare_results(candidates)
    print(
        build_run_report(
            comparison=comparison,
            experiment_name=experiment_name,
            tenant_slug=args.tenant,
            project_slug=args.project,
            holdout_size=args.holdout_size,
        )
    )
    _register_comparison(
        comparison=comparison,
        scope=scope,
        tenant_slug=args.tenant,
        project_slug=args.project,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        print(f"\nResultados no MLflow: {MLFLOW_TRACKING_URI}")


if __name__ == "__main__":
    main()
