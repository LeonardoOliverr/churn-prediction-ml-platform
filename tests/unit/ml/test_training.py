"""
Testes unitários para ml/core/training.py.

Inclui:
- _cv_metrics(): retorno de chaves e tipos
- train_with_cv(): comportamento com e sem holdout
"""

import numpy as np
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from unittest.mock import MagicMock, patch

from ml.config.settings import TARGET
from ml.data.preprocessing import build_preprocessor
from ml.core.training import CV, SCORING


_FAKE_CV_RESULTS = {
    **{f"test_{m}":  np.array([0.5, 0.6, 0.55, 0.58, 0.52]) for m in SCORING},
    **{f"train_{m}": np.array([0.8, 0.82, 0.81, 0.80, 0.79]) for m in SCORING},
}


# ---------------------------------------------------------------------------
# _cv_metrics()
# ---------------------------------------------------------------------------


def test_cv_metrics_returns_expected_keys(fake_customers_df):
    """_cv_metrics() retorna todas as chaves de métricas esperadas."""
    from ml.core.training import _cv_metrics

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", DummyClassifier(strategy="stratified", random_state=42)),
    ])

    with patch("ml.core.training.metrics.cross_validate", return_value=_FAKE_CV_RESULTS):
        metrics = _cv_metrics(pipeline, X, y)

    expected_keys = (
        [f"{m}_{stat}" for m in SCORING for stat in ("mean", "std")]
        + [f"train_{m}_mean" for m in SCORING]
    )
    for key in expected_keys:
        assert key in metrics, f"Chave ausente em metrics: '{key}'"


def test_cv_metrics_values_are_floats(fake_customers_df):
    """Todos os valores retornados por _cv_metrics() são float."""
    from ml.core.training import _cv_metrics

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", DummyClassifier(strategy="stratified", random_state=42)),
    ])

    with patch("ml.core.training.metrics.cross_validate", return_value=_FAKE_CV_RESULTS):
        metrics = _cv_metrics(pipeline, X, y)

    for key, value in metrics.items():
        assert isinstance(value, float), f"'{key}' deveria ser float, got {type(value)}"


# ---------------------------------------------------------------------------
# train_with_cv() — sem holdout (holdout_size=0.0)
# ---------------------------------------------------------------------------


def test_train_with_cv_no_holdout_returns_pipeline_and_metrics(fake_customers_df):
    """train_with_cv com holdout_size=0.0 retorna 'pipeline' e 'metrics'."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("baseline")[0]
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_metrics = {f"{m}_mean": 0.5 for m in SCORING}
    fake_metrics.update({f"{m}_std": 0.0 for m in SCORING})
    fake_metrics.update({f"train_{m}_mean": 0.8 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_metrics):
        result = train_with_cv(spec, X, y, holdout_size=0.0)

    assert "pipeline" in result
    assert "metrics" in result


def test_train_with_cv_no_holdout_metrics_equal_cv_metrics(fake_customers_df):
    """train_with_cv com holdout_size=0.0 usa diretamente as métricas do CV."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("baseline")[0]
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_metrics = {f"{m}_mean": 0.5 for m in SCORING}
    fake_metrics.update({f"{m}_std": 0.01 for m in SCORING})
    fake_metrics.update({f"train_{m}_mean": 0.8 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_metrics):
        result = train_with_cv(spec, X, y, holdout_size=0.0)

    assert result["metrics"]["f1_mean"] == 0.5
    assert result["metrics"]["f1_std"] == 0.01


# ---------------------------------------------------------------------------
# train_with_cv() — com holdout (holdout_size=0.2)
# ---------------------------------------------------------------------------


def test_train_with_cv_with_holdout_returns_pipeline_and_metrics(fake_customers_df):
    """train_with_cv com holdout separado retorna dict com pipeline e metrics."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("baseline")[1]  # logistic_regression
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_cv = {f"{m}_mean": 0.6 for m in SCORING}
    fake_cv.update({f"{m}_std": 0.02 for m in SCORING})
    fake_cv.update({f"train_{m}_mean": 0.85 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_cv):
        result = train_with_cv(spec, X, y, holdout_size=0.2)

    assert "pipeline" in result
    assert "metrics" in result


def test_train_with_cv_holdout_pipeline_is_fitted(fake_customers_df):
    """Pipeline retornado por train_with_cv está fitado (possui classes_)."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("baseline")[0]  # DummyClassifier
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_cv = {f"{m}_mean": 0.5 for m in SCORING}
    fake_cv.update({f"{m}_std": 0.0 for m in SCORING})
    fake_cv.update({f"train_{m}_mean": 0.5 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_cv):
        result = train_with_cv(spec, X, y, holdout_size=0.2)

    assert hasattr(result["pipeline"].named_steps["classifier"], "classes_")


def test_train_with_cv_holdout_metrics_format(fake_customers_df):
    """Com holdout, dict de métricas tem chaves primárias, cv_ e train_."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("baseline")[1]
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_cv = {f"{m}_mean": 0.6 for m in SCORING}
    fake_cv.update({f"{m}_std": 0.02 for m in SCORING})
    fake_cv.update({f"train_{m}_mean": 0.85 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_cv):
        result = train_with_cv(spec, X, y, holdout_size=0.2)

    metrics = result["metrics"]
    assert "f1_mean" in metrics
    assert "cv_f1_mean" in metrics
    assert "train_f1_mean" in metrics
    assert metrics["f1_std"] == 0.0


def test_train_with_cv_holdout_separates_approx_20_percent(fake_customers_df):
    """Holdout tem aproximadamente holdout_size% dos dados originais."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("baseline")[0]
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    n_total = len(X)

    fake_cv = {f"{m}_mean": 0.5 for m in SCORING}
    fake_cv.update({f"{m}_std": 0.0 for m in SCORING})
    fake_cv.update({f"train_{m}_mean": 0.5 for m in SCORING})

    captured_X_train = {}

    original_cv_metrics = __import__("ml.core.training", fromlist=["_cv_metrics"])._cv_metrics

    def mock_cv(pipeline, X, y):
        captured_X_train["n"] = len(X)
        return fake_cv

    with patch("ml.core.training.train._cv_metrics", side_effect=mock_cv):
        train_with_cv(spec, X, y, holdout_size=0.2)

    n_train = captured_X_train["n"]
    assert n_train < n_total
    assert abs(n_train / n_total - 0.8) < 0.1


def test_train_with_cv_applies_hp_overrides(fake_customers_df):
    """hp_overrides são repassados ao estimator_factory do spec."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = _resolve_specs("random_forest")[0]
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_cv = {f"{m}_mean": 0.7 for m in SCORING}
    fake_cv.update({f"{m}_std": 0.01 for m in SCORING})
    fake_cv.update({f"train_{m}_mean": 0.9 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_cv):
        result = train_with_cv(spec, X, y, hp_overrides={"n_estimators": 7}, holdout_size=0.2)

    classifier = result["pipeline"].named_steps["classifier"]
    assert classifier.n_estimators == 7
    assert classifier.max_features == "sqrt"
    assert classifier.class_weight == "balanced"
    assert classifier.random_state == 42
    assert classifier.n_jobs == -1


def test_train_with_cv_uses_logistic_regression_fixed_params(fake_customers_df):
    """Logistic Regression treina com os fixed_params declarados no ModelSpec."""
    from ml.core.training import train_with_cv
    from ml.train import _resolve_specs

    spec = next(s for s in _resolve_specs("baseline") if s.name == "logistic_regression")
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    fake_cv = {f"{m}_mean": 0.7 for m in SCORING}
    fake_cv.update({f"{m}_std": 0.01 for m in SCORING})
    fake_cv.update({f"train_{m}_mean": 0.9 for m in SCORING})

    with patch("ml.core.training.train._cv_metrics", return_value=fake_cv):
        result = train_with_cv(spec, X, y, holdout_size=0.0)

    classifier = result["pipeline"].named_steps["classifier"]
    assert classifier.max_iter == 1000
    assert classifier.random_state == 42
    assert classifier.class_weight == "balanced"
