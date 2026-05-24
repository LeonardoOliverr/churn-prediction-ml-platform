"""Model definitions exposed as declarative ModelSpec objects."""

from ml.models.baseline import SPECS as BASELINE_SPECS
from ml.models.random_forest import SPECS as RANDOM_FOREST_SPECS
from ml.models.xgboost import SPECS as XGBOOST_SPECS

__all__ = ["BASELINE_SPECS", "RANDOM_FOREST_SPECS", "XGBOOST_SPECS"]
