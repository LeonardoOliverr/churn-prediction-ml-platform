"""Módulo de explicabilidade — SHAP wrappers para modelos sklearn/XGBoost."""

from ml.explainability.shap_explainer import build_explainer, top_shap_values

__all__ = ["build_explainer", "top_shap_values"]
