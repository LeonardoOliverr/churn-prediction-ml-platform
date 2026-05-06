"""Generic training pipeline with cross-validation and optional fixed holdout."""

from __future__ import annotations

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.core.model_spec import ModelSpec
from ml.core.training.metrics import CV, SCORING, _compute_score, _cv_metrics
from ml.data.preprocessing import build_preprocessor


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

    print(f"\n[{spec.name}] Executando cross-validation ({CV.n_splits} folds)...")
    cv_metrics = _cv_metrics(pipeline, X_train, y_train)

    cv_f1_gap = cv_metrics["train_f1_mean"] - cv_metrics["f1_mean"]
    cv_roc_gap = cv_metrics["train_roc_auc_mean"] - cv_metrics["roc_auc_mean"]
    gap_warning = "  overfitting" if cv_f1_gap > 0.10 else ""

    print(f"  CV F1        : treino={cv_metrics['train_f1_mean']:.4f}  val={cv_metrics['f1_mean']:.4f} +/- {cv_metrics['f1_std']:.4f}  gap={cv_f1_gap:+.4f}{gap_warning}")
    print(f"  CV ROC-AUC   : treino={cv_metrics['train_roc_auc_mean']:.4f}  val={cv_metrics['roc_auc_mean']:.4f} +/- {cv_metrics['roc_auc_std']:.4f}  gap={cv_roc_gap:+.4f}")
    print(f"  CV Recall    : {cv_metrics['recall_mean']:.4f}")
    print(f"  CV Precision : {cv_metrics['precision_mean']:.4f}")

    pipeline.fit(X_train, y_train)

    if X_holdout is not None:
        holdout_scores = {
            metric: _compute_score(pipeline, X_holdout, y_holdout, metric)
            for metric in SCORING
        }

        ho_f1_gap = cv_metrics["train_f1_mean"] - holdout_scores["f1"]
        print(f"\n  Holdout F1        : {holdout_scores['f1']:.4f}  gap vs CV-treino={ho_f1_gap:+.4f}")
        print(f"  Holdout ROC-AUC   : {holdout_scores['roc_auc']:.4f}")
        print(f"  Holdout Recall    : {holdout_scores['recall']:.4f}")
        print(f"  Holdout Precision : {holdout_scores['precision']:.4f}")

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
