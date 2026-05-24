"""Random Forest model definition."""

from ml.core.model_spec import ModelSpec


def _random_forest_classifier(**params):
    from sklearn.ensemble import RandomForestClassifier

    fixed_params = {
        "max_features": "sqrt",
        "class_weight": "balanced",
        "random_state": 42,
        "n_jobs": -1,
    }
    return RandomForestClassifier(**{**fixed_params, **params})


SPECS = [
    ModelSpec(
        name="random_forest",
        estimator_factory=_random_forest_classifier,
        default_params={"n_estimators": 500, "max_depth": None},
        fixed_params={
            "max_features": "sqrt",
            "class_weight": "balanced",
            "random_state": 42,
            "n_jobs": -1,
        },
        cli_overrides={"n_estimators": int, "max_depth": int},
        experiment_suffix="random-forest",
        log_feature_importances=True,
    ),
]
