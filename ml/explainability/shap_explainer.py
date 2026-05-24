"""Wrapper de SHAP para modelos sklearn/XGBoost do projeto.

Estratégia por tipo de modelo:
- XGBoost  → pred_contribs=True nativo (sem importar shap, dezenas de vezes mais rápido)
- RF       → shap.TreeExplainer (requer pacote shap)
- LR       → shap.LinearExplainer (requer pacote shap + X_background)
"""

import numpy as np

_XGBOOST_MODELS = ("XGBClassifier",)
_RF_MODELS = ("RandomForestClassifier",)
_TOP_N_DEFAULT = 5


def compute_shap_values(
    pipeline,
    X_transformed: np.ndarray,
    feature_names: list[str],
    top_n: int = _TOP_N_DEFAULT,
) -> list[dict]:
    """Ponto de entrada unificado para cálculo de SHAP.

    Escolhe automaticamente a estratégia mais eficiente por tipo de modelo:
    XGBoost usa API nativa (sem lib shap); RF e LR usam shap.TreeExplainer/LinearExplainer.
    """
    estimator = pipeline.named_steps.get("classifier") or pipeline[-1]
    class_name = type(estimator).__name__

    if class_name in _XGBOOST_MODELS:
        return _shap_xgboost_native(estimator, X_transformed, feature_names, top_n)

    return _shap_via_library(estimator, class_name, X_transformed, feature_names, top_n)


def _shap_xgboost_native(
    estimator,
    X_transformed: np.ndarray,
    feature_names: list[str],
    top_n: int,
) -> list[dict]:
    """Calcula contribuições SHAP via pred_contribs=True do XGBoost.

    Não importa o pacote shap — usa a API nativa do booster.
    Retorna valores no espaço log-odds (escala aditiva logística).
    A última coluna de pred_contribs é o bias (intercepto) — descartada.
    """
    import xgboost as xgb

    booster = estimator.get_booster()
    dmatrix = xgb.DMatrix(X_transformed)
    contribs = booster.predict(dmatrix, pred_contribs=True)
    contribs = contribs[:, :-1]  # remove coluna de bias

    return _rank_top_n(contribs, feature_names, top_n)


def _shap_via_library(
    estimator,
    class_name: str,
    X_transformed: np.ndarray,
    feature_names: list[str],
    top_n: int,
) -> list[dict]:
    """Calcula SHAP via pacote shap para RF e modelos lineares."""
    import shap

    if class_name in _RF_MODELS:
        explainer = shap.TreeExplainer(estimator)
    else:
        explainer = shap.LinearExplainer(
            estimator, masker=shap.maskers.Independent(data=X_transformed)
        )

    shap_vals = explainer.shap_values(X_transformed)

    # SHAP >=0.45 (nova API): array 3D (n_samples, n_features, n_classes)
    if isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
        shap_vals = shap_vals[:, :, 1]
    # API antiga: lista [class0_vals, class1_vals]
    elif isinstance(shap_vals, list):
        shap_vals = shap_vals[1]

    return _rank_top_n(shap_vals, feature_names, top_n)


def _rank_top_n(contribs: np.ndarray, feature_names: list[str], top_n: int) -> list[dict]:
    """Ordena features por |contribuição| desc e retorna os top-N por linha."""
    results = []
    for row in contribs:
        pairs = sorted(
            zip(feature_names, row.tolist(), strict=False),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        results.append({name: round(val, 6) for name, val in pairs[:top_n]})
    return results


# ---------------------------------------------------------------------------
# API legada — mantida para compatibilidade com testes e uso externo
# ---------------------------------------------------------------------------


def build_explainer(pipeline, X_background: np.ndarray | None = None):
    """Constrói TreeExplainer ou LinearExplainer conforme o estimador final do pipeline.

    Prefira compute_shap_values() para uso em produção — escolhe a estratégia
    mais eficiente por modelo (XGBoost nativo, RF via shap, LR via shap).
    X_background é obrigatório para modelos lineares (LogisticRegression).
    """
    import shap

    estimator = pipeline.named_steps.get("classifier") or pipeline[-1]
    class_name = type(estimator).__name__

    if class_name in (*_XGBOOST_MODELS, *_RF_MODELS):
        return shap.TreeExplainer(estimator)

    if X_background is None:
        raise ValueError(
            "X_background (dados transformados) é obrigatório para LinearExplainer. "
            "Passe pipeline.named_steps['preprocessor'].transform(X)."
        )
    return shap.LinearExplainer(estimator, masker=shap.maskers.Independent(data=X_background))


def top_shap_values(
    explainer,
    X_transformed: np.ndarray,
    feature_names: list[str],
    top_n: int = _TOP_N_DEFAULT,
) -> list[dict]:
    """Retorna top-N valores SHAP por linha usando um explainer já construído.

    Prefira compute_shap_values() para uso em produção.
    """
    shap_vals = explainer.shap_values(X_transformed)

    if isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
        shap_vals = shap_vals[:, :, 1]
    elif isinstance(shap_vals, list):
        shap_vals = shap_vals[1]

    return _rank_top_n(shap_vals, feature_names, top_n)
