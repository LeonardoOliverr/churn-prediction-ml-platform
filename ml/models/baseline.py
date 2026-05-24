"""Baseline model definitions."""

from ml.core.model_spec import ModelSpec


def _dummy_classifier(**params):
    from sklearn.dummy import DummyClassifier

    fixed_params = {"strategy": "stratified", "random_state": 42}
    return DummyClassifier(**{**fixed_params, **params})


def _logistic_regression(**params):
    from sklearn.linear_model import LogisticRegression

    fixed_params = {"max_iter": 1000, "random_state": 42, "class_weight": "balanced"}
    return LogisticRegression(**{**fixed_params, **params})


SPECS = [
    ModelSpec(
        name="dummy_stratified",
        estimator_factory=_dummy_classifier,
        default_params={},
        fixed_params={"strategy": "stratified", "random_state": 42},
        cli_overrides={},
        experiment_suffix="baseline",
        log_feature_importances=False,
    ),
    ModelSpec(
        name="logistic_regression",
        estimator_factory=_logistic_regression,
        default_params={},
        fixed_params={"max_iter": 1000, "random_state": 42, "class_weight": "balanced"},
        cli_overrides={},
        experiment_suffix="baseline",
        log_feature_importances=False,
    ),
]
