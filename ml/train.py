"""CLI unificado de treinamento.

Uso:
    python -m ml.train --model baseline --tenant X --project Y [--dry-run]
    python -m ml.train --model random_forest --tenant X --project Y [--n-estimators 300]
    python -m ml.train --model xgboost --tenant X --project Y
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from core.logger import get_logger
from ml.config.settings import MLFLOW_TRACKING_URI
from ml.core.training.metrics import CV
from ml.evaluation import CandidateResult, build_run_report, compare_results

logger = get_logger()

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
        choices=["baseline", "random_forest", "xgboost"],
        help="Familia de modelos a treinar.",
    )
    parser.add_argument(
        "--tenant",
        required=True,
        help="Slug do tenant.",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Slug do projeto.",
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
        help="Numero de estimadores (arvores).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Profundidade maxima das arvores.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=None,
        help="Taxa de aprendizado (XGBoost).",
    )
    parser.add_argument(
        "--subsample",
        type=float,
        default=None,
        help="Fracao de amostras por arvore (XGBoost).",
    )
    parser.add_argument(
        "--colsample-bytree",
        type=float,
        default=None,
        help="Fracao de features por arvore (XGBoost).",
    )
    parser.add_argument(
        "--scale-pos-weight",
        type=float,
        default=None,
        help="Peso da classe positiva para desbalanceamento (XGBoost).",
    )
    parser.add_argument(
        "--reg-alpha",
        type=float,
        default=None,
        help="Regularizacao L1 (XGBoost).",
    )
    parser.add_argument(
        "--reg-lambda",
        type=float,
        default=None,
        help="Regularizacao L2 (XGBoost).",
    )
    parser.add_argument(
        "--min-child-weight",
        type=int,
        default=None,
        help="Peso minimo por folha — aumentar reduz overfitting (XGBoost).",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=None,
        help="Reducao minima de loss para split — aumentar reduz overfitting (XGBoost).",
    )
    args = parser.parse_args()

    return args


def _resolve_specs(model_name: str) -> list[ModelSpec]:
    """Retorna a lista de ModelSpec para o modelo solicitado."""
    from ml.models import BASELINE_SPECS, RANDOM_FOREST_SPECS, XGBOOST_SPECS

    if model_name == "baseline":
        return BASELINE_SPECS
    if model_name == "random_forest":
        return RANDOM_FOREST_SPECS
    if model_name == "xgboost":
        return XGBOOST_SPECS
    raise ValueError(f"Modelo desconhecido: {model_name!r}")


def _derive_scope(
    tenant_slug: str,
    project_slug: str,
    experiment_suffix: str,
) -> tuple[str, str]:
    """Retorna (scope, experiment_name) a partir dos slugs e do sufixo."""
    return "project", f"{tenant_slug}/{project_slug}/{experiment_suffix}"


def _db_name(spec_name: str) -> str:
    """Gera o nome do modelo para registro em churn.models."""
    return spec_name.replace("_", "-")


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
    candidates = {
        "n_estimators": getattr(args, "n_estimators", None),
        "max_depth": getattr(args, "max_depth", None),
        "learning_rate": getattr(args, "learning_rate", None),
        "subsample": getattr(args, "subsample", None),
        "colsample_bytree": getattr(args, "colsample_bytree", None),
        "scale_pos_weight": getattr(args, "scale_pos_weight", None),
        "reg_alpha": getattr(args, "reg_alpha", None),
        "reg_lambda": getattr(args, "reg_lambda", None),
        "min_child_weight": getattr(args, "min_child_weight", None),
        "gamma": getattr(args, "gamma", None),
    }
    return {k: v for k, v in candidates.items() if v is not None}


def _log_run_context(
    scope: str,
    tenant_slug: str,
    project_slug: str,
    experiment_name: str,
    holdout_size: float,
) -> None:
    logger.info(
        "run_context",
        scope=scope,
        tenant=tenant_slug,
        project=project_slug,
        experiment=experiment_name,
        holdout=f"{holdout_size:.0%}" if holdout_size > 0 else "disabled",
    )


def _train_candidates(
    specs: list[ModelSpec],
    X,
    y,
    args: argparse.Namespace,
    hp_overrides: dict,
) -> list[CandidateResult]:
    """Executa treino e logging, retornando candidatos avaliaveis pelo run."""
    train_row_count = len(X)
    churn_rate = round(float(y.mean()), 4)

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
        metrics = {
            **result["metrics"],
            "train_row_count": train_row_count,
            "churn_rate": churn_rate,
        }

        if args.dry_run:
            logger.warning("mlflow_run_skipped", reason="dry_run")
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
    tenant_slug: str | None,
    project_slug: str | None,
    dry_run: bool,
) -> None:
    """Registra todos os candidatos com o status decidido pela comparacao."""
    for candidate in comparison.candidates:
        db_name = _db_name(candidate.spec.name)
        register_in_db(
            name=db_name,
            run_id=candidate.run_id,
            metrics=candidate.metrics,
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
        logger.warning("dry_run_mode", message="nenhuma escrita sera realizada")

    _log_run_context(
        scope=scope,
        tenant_slug=args.tenant,
        project_slug=args.project,
        experiment_name=experiment_name,
        holdout_size=args.holdout_size,
    )

    if not args.dry_run:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(experiment_name)

    logger.info("data_loading_started")
    X, y = load_data(tenant_slug=args.tenant, project_slug=args.project)
    logger.info("data_loaded", records=len(X), churn_rate=round(float(y.mean()), 4))

    hp_overrides = _hp_overrides_from_args(args)
    candidates = _train_candidates(specs, X, y, args, hp_overrides)
    comparison = compare_results(candidates)
    logger.info(
        "training_run_report",
        report=build_run_report(
            comparison=comparison,
            experiment_name=experiment_name,
            tenant_slug=args.tenant,
            project_slug=args.project,
            holdout_size=args.holdout_size,
        ),
    )
    _register_comparison(
        comparison=comparison,
        tenant_slug=args.tenant,
        project_slug=args.project,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        logger.info("mlflow_results", uri=MLFLOW_TRACKING_URI)


if __name__ == "__main__":
    main()
