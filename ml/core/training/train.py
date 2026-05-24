"""Generic training pipeline with cross-validation and optional fixed holdout."""

from __future__ import annotations

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from core.logger import get_logger
from ml.core.model_spec import ModelSpec
from ml.core.training.metrics import CV, SCORING, _compute_score, _cv_metrics
from ml.data.preprocessing import build_preprocessor

logger = get_logger()


def train_with_cv(
    spec: ModelSpec,
    X,
    y,
    hp_overrides: dict | None = None,
    holdout_size: float = 0.2,
) -> dict:
    """Train with CV and evaluate on a fixed holdout when enabled."""
    if hp_overrides is None:
        hp_overrides = {}

    merged = {**spec.default_params, **hp_overrides, **spec.fixed_params}
    estimator = spec.estimator_factory(**merged)
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", estimator),
        ]
    )

    if holdout_size > 0.0:
        X_train, X_holdout, y_train, y_holdout = train_test_split(
            X,
            y,
            test_size=holdout_size,
            stratify=y,
            random_state=42,
        )
    else:
        X_train, y_train = X, y
        X_holdout, y_holdout = None, None

    logger.info("cv_started", model=spec.name, n_splits=CV.n_splits)
    cv_metrics = _cv_metrics(pipeline, X_train, y_train)

    cv_f1_gap = cv_metrics["train_f1_mean"] - cv_metrics["f1_mean"]
    cv_roc_gap = cv_metrics["train_roc_auc_mean"] - cv_metrics["roc_auc_mean"]

    logger.info(
        "cv_metrics",
        model=spec.name,
        train_f1=round(cv_metrics["train_f1_mean"], 4),
        val_f1=round(cv_metrics["f1_mean"], 4),
        val_f1_std=round(cv_metrics["f1_std"], 4),
        cv_f1_gap=round(cv_f1_gap, 4),
        train_roc_auc=round(cv_metrics["train_roc_auc_mean"], 4),
        val_roc_auc=round(cv_metrics["roc_auc_mean"], 4),
        val_roc_auc_std=round(cv_metrics["roc_auc_std"], 4),
        cv_roc_gap=round(cv_roc_gap, 4),
        recall=round(cv_metrics["recall_mean"], 4),
        precision=round(cv_metrics["precision_mean"], 4),
        overfitting=cv_f1_gap > 0.10,
    )

    pipeline.fit(X_train, y_train)

    if X_holdout is not None:
        holdout_scores = {
            metric: _compute_score(pipeline, X_holdout, y_holdout, metric) for metric in SCORING
        }

        ho_f1_gap = cv_metrics["train_f1_mean"] - holdout_scores["f1"]
        logger.info(
            "holdout_metrics",
            model=spec.name,
            f1=round(holdout_scores["f1"], 4),
            ho_f1_gap=round(ho_f1_gap, 4),
            roc_auc=round(holdout_scores["roc_auc"], 4),
            recall=round(holdout_scores["recall"], 4),
            precision=round(holdout_scores["precision"], 4),
        )

        metrics: dict[str, float] = {
            "f1_mean": holdout_scores["f1"],
            "f1_std": 0.0,
            "roc_auc_mean": holdout_scores["roc_auc"],
            "roc_auc_std": 0.0,
            "recall_mean": holdout_scores["recall"],
            "recall_std": 0.0,
            "precision_mean": holdout_scores["precision"],
            "precision_std": 0.0,
            "cv_f1_mean": cv_metrics["f1_mean"],
            "cv_f1_std": cv_metrics["f1_std"],
            "cv_roc_auc_mean": cv_metrics["roc_auc_mean"],
            "cv_roc_auc_std": cv_metrics["roc_auc_std"],
            "cv_recall_mean": cv_metrics["recall_mean"],
            "cv_recall_std": cv_metrics["recall_std"],
            "cv_precision_mean": cv_metrics["precision_mean"],
            "cv_precision_std": cv_metrics["precision_std"],
            "train_f1_mean": cv_metrics["train_f1_mean"],
            "train_roc_auc_mean": cv_metrics["train_roc_auc_mean"],
            "train_recall_mean": cv_metrics["train_recall_mean"],
            "train_precision_mean": cv_metrics["train_precision_mean"],
        }
    else:
        metrics = cv_metrics

    return {"pipeline": pipeline, "metrics": metrics}
