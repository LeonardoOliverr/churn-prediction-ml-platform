"""Baseline model definitions."""

from ml.core.model_spec import ModelSpec


def _dummy_classifier(**_):
    from sklearn.dummy import DummyClassifier

    return DummyClassifier(strategy="stratified", random_state=42)


def _logistic_regression(**_):
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
    )


SPECS = [
    ModelSpec(
        name="dummy_stratified",
        estimator_factory=_dummy_classifier,
        default_params={},
        cli_overrides={},
        experiment_suffix="baseline",
        log_feature_importances=False,
    ),
    ModelSpec(
        name="logistic_regression",
        estimator_factory=_logistic_regression,
        default_params={},
        cli_overrides={},
        experiment_suffix="baseline",
        log_feature_importances=False,
    ),
]
