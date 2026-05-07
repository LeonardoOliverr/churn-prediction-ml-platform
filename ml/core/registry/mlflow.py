"""MLflow logging for trained sklearn pipelines."""

from __future__ import annotations

import os
import tempfile

import mlflow
import mlflow.sklearn
from sklearn.pipeline import Pipeline

from ml.core.logger import get_logger

logger = get_logger()


def _get_feature_names(pipeline: Pipeline) -> list[str]:
    """Extract transformed feature names from the fitted ColumnTransformer."""
    preprocessor = pipeline.named_steps["preprocessor"]
    raw = preprocessor.get_feature_names_out()
    return [name.split("__", 1)[-1] if "__" in name else name for name in raw.tolist()]


def log_to_mlflow(
    run_name: str,
    params: dict,
    metrics: dict,
    pipeline: Pipeline,
    log_feature_importances: bool = False,
) -> str:
    """Log metrics and a fitted sklearn pipeline to MLflow."""
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        with tempfile.TemporaryDirectory() as tmp:
            model_path = os.path.join(tmp, "model")
            mlflow.sklearn.save_model(pipeline, model_path)
            mlflow.log_artifacts(model_path, artifact_path="model")

        if log_feature_importances:
            feature_names = _get_feature_names(pipeline)
            importances = pipeline.named_steps["classifier"].feature_importances_
            importance_map = dict(
                sorted(
                    zip(feature_names, importances.tolist()),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
            try:
                mlflow.log_dict(importance_map, "feature_importances.json")
            except Exception as e:
                logger.warning("feature_importances_not_saved", error=str(e))

            top5 = list(importance_map.items())[:5]
            logger.info(
                "top_features",
                features={feat: round(imp, 4) for feat, imp in top5},
            )

        return run.info.run_id
