"""XGBoost model definition."""

from ml.core.model_spec import ModelSpec


def _xgboost_classifier(**params):
    from xgboost import XGBClassifier

    return XGBClassifier(**params)


SPECS = [
    ModelSpec(
        name="xgboost",
        estimator_factory=_xgboost_classifier,
        default_params={
            "n_estimators": 500,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.7,
            "colsample_bytree": 0.7,
            "scale_pos_weight": 2.7,
            "reg_alpha": 0.1,
            "reg_lambda": 2.0,
        },
        fixed_params={
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "random_state": 42,
            "n_jobs": -1,
        },
        cli_overrides={
            "n_estimators": int,
            "max_depth": int,
            "learning_rate": float,
            "subsample": float,
            "colsample_bytree": float,
            "scale_pos_weight": float,
            "reg_alpha": float,
            "reg_lambda": float,
            "min_child_weight": int,
            "gamma": float,
        },
        experiment_suffix="xgboost",
        log_feature_importances=True,
    ),
]
