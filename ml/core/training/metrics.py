"""Training metrics and cross-validation helpers."""

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline

CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
SCORING = ["f1", "roc_auc", "recall", "precision"]


def _cv_metrics(pipeline: Pipeline, X, y) -> dict[str, float]:
    """Run cross-validation and return train/test metrics by fold."""
    results = cross_validate(pipeline, X, y, cv=CV, scoring=SCORING, return_train_score=True)
    metrics: dict[str, float] = {}
    for metric in SCORING:
        test_scores = results[f"test_{metric}"]
        train_scores = results[f"train_{metric}"]
        metrics[f"{metric}_mean"] = float(np.mean(test_scores))
        metrics[f"{metric}_std"] = float(np.std(test_scores))
        metrics[f"train_{metric}_mean"] = float(np.mean(train_scores))
    return metrics


def _compute_score(pipeline: Pipeline, X, y, metric: str) -> float:
    """Compute one sklearn metric on an already split dataset."""
    y_pred = pipeline.predict(X)
    if metric == "f1":
        return float(f1_score(y, y_pred))
    if metric == "roc_auc":
        y_proba = pipeline.predict_proba(X)[:, 1]
        return float(roc_auc_score(y, y_proba))
    if metric == "recall":
        return float(recall_score(y, y_pred))
    if metric == "precision":
        return float(precision_score(y, y_pred))
    raise ValueError(f"Unknown metric: {metric}")
