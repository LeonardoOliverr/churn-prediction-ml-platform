"""
Testes para ml/explainability/shap_explainer.py.

Inclui:
- [SMOKE TEST] build_explainer + top_shap_values com RandomForest real
- Verificação de tipo de explainer por classe de modelo
- Estrutura e ordenação de top_shap_values
- Comportamento com shap_vals como lista (classificação binária)
"""

from unittest.mock import MagicMock

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.config.settings import TARGET
from ml.data.preprocessing import build_preprocessor
from ml.explainability.shap_explainer import (
    build_explainer,
    compute_shap_values,
    top_shap_values,
)

# ---------------------------------------------------------------------------
# Fixtures auxiliares
# ---------------------------------------------------------------------------


@pytest.fixture
def rf_pipeline(fake_customers_df):
    """Pipeline RandomForest treinado com dados fake."""
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(n_estimators=10, random_state=42)),
        ]
    )
    pipeline.fit(X, y)
    return pipeline


@pytest.fixture
def lr_pipeline(fake_customers_df):
    """Pipeline LogisticRegression treinado com dados fake."""
    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", LogisticRegression(max_iter=500, random_state=42)),
        ]
    )
    pipeline.fit(X, y)
    return pipeline


@pytest.fixture
def X_transformed(rf_pipeline, fake_customers_df):
    """Array transformado pelo preprocessor do pipeline RF."""
    X = fake_customers_df.drop(columns=[TARGET])
    raw = rf_pipeline.named_steps["preprocessor"].transform(X)
    return raw.toarray() if hasattr(raw, "toarray") else raw


@pytest.fixture
def feature_names(rf_pipeline):
    """Nomes das features após pré-processamento."""
    preprocessor = rf_pipeline.named_steps["preprocessor"]
    raw = preprocessor.get_feature_names_out()
    return [name.split("__", 1)[-1] if "__" in name else name for name in raw.tolist()]


# ---------------------------------------------------------------------------
# SMOKE TEST — fluxo end-to-end com RF real
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_smoke_shap_rf(rf_pipeline, X_transformed, feature_names):
    """[SMOKE TEST] build_explainer + top_shap_values retornam lista de dicts válidos."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names, top_n=5)

    assert len(results) == X_transformed.shape[0]
    for record in results:
        assert isinstance(record, dict)
        assert len(record) == 5
        for key, val in record.items():
            assert isinstance(key, str)
            assert isinstance(val, float)


# ---------------------------------------------------------------------------
# SMOKE TEST — XGBoost nativo (sem lib shap)
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_smoke_shap_xgboost_native(fake_customers_df):
    """[SMOKE TEST] compute_shap_values usa pred_contribs nativo para XGBoost."""
    from xgboost import XGBClassifier

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=10,
                    max_depth=3,
                    random_state=42,
                    eval_metric="auc",
                    objective="binary:logistic",
                ),
            ),
        ]
    )
    pipeline.fit(X, y)

    preprocessor = pipeline.named_steps["preprocessor"]
    raw = preprocessor.transform(X)
    X_t = raw.toarray() if hasattr(raw, "toarray") else raw

    from ml.core.registry.mlflow import _get_feature_names

    feature_names = _get_feature_names(pipeline)

    results = compute_shap_values(pipeline, X_t, feature_names, top_n=5)

    assert len(results) == X_t.shape[0]
    for record in results:
        assert isinstance(record, dict)
        assert len(record) == 5
        for key, val in record.items():
            assert isinstance(key, str)
            assert isinstance(val, float)


# ---------------------------------------------------------------------------
# build_explainer — tipo de explainer por classe de modelo
# ---------------------------------------------------------------------------


def test_build_explainer_rf_returns_tree_explainer(rf_pipeline):
    """RandomForest produz TreeExplainer."""
    import shap

    explainer = build_explainer(rf_pipeline)
    assert isinstance(explainer, shap.TreeExplainer)


def test_build_explainer_lr_returns_linear_explainer(lr_pipeline, fake_customers_df):
    """LogisticRegression produz LinearExplainer quando X_background é fornecido."""
    import shap

    X = fake_customers_df.drop(columns=[TARGET])
    raw = lr_pipeline.named_steps["preprocessor"].transform(X)
    X_bg = raw.toarray() if hasattr(raw, "toarray") else raw

    explainer = build_explainer(lr_pipeline, X_background=X_bg)
    assert isinstance(explainer, shap.LinearExplainer)


def test_build_explainer_lr_without_background_raises(lr_pipeline):
    """build_explainer sem X_background para modelo linear levanta ValueError."""
    with pytest.raises(ValueError, match="X_background"):
        build_explainer(lr_pipeline)


def test_build_explainer_uses_named_step_classifier(rf_pipeline):
    """build_explainer acessa o step 'classifier' do pipeline."""
    estimator = rf_pipeline.named_steps["classifier"]
    assert type(estimator).__name__ == "RandomForestClassifier"


# ---------------------------------------------------------------------------
# top_shap_values — estrutura e ordenação
# ---------------------------------------------------------------------------


def test_top_shap_values_respects_top_n(rf_pipeline, X_transformed, feature_names):
    """top_shap_values retorna exatamente top_n features por linha."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names, top_n=3)
    for record in results:
        assert len(record) == 3


def test_top_shap_values_ordered_by_abs_descending(rf_pipeline, X_transformed, feature_names):
    """Os valores SHAP estão em ordem decrescente de valor absoluto."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names, top_n=5)
    for record in results:
        vals = list(record.values())
        abs_vals = [abs(v) for v in vals]
        assert abs_vals == sorted(abs_vals, reverse=True)


def test_top_shap_values_rounds_to_6_decimals(rf_pipeline, X_transformed, feature_names):
    """Valores SHAP são arredondados para 6 casas decimais."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names, top_n=5)
    for record in results:
        for val in record.values():
            assert val == round(val, 6)


def test_top_shap_values_feature_names_are_strings(rf_pipeline, X_transformed, feature_names):
    """As chaves de cada dict são strings."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names, top_n=5)
    for record in results:
        for key in record:
            assert isinstance(key, str)


def test_top_shap_values_handles_list_shap_vals():
    """top_shap_values lida com explainer.shap_values() retornando lista [class0, class1]."""
    n_rows, n_features = 4, 10
    feature_names = [f"f{i}" for i in range(n_features)]
    class0_vals = np.zeros((n_rows, n_features))
    class1_vals = np.random.randn(n_rows, n_features)

    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = [class0_vals, class1_vals]

    results = top_shap_values(
        mock_explainer, np.zeros((n_rows, n_features)), feature_names, top_n=5
    )

    assert len(results) == n_rows
    for record in results:
        assert len(record) == 5


def test_top_shap_values_handles_2d_array_shap_vals():
    """top_shap_values funciona quando shap_values retorna array 2D diretamente."""
    n_rows, n_features = 4, 10
    feature_names = [f"f{i}" for i in range(n_features)]
    shap_array = np.random.randn(n_rows, n_features)

    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = shap_array

    results = top_shap_values(
        mock_explainer, np.zeros((n_rows, n_features)), feature_names, top_n=3
    )

    assert len(results) == n_rows
    for record in results:
        assert len(record) == 3


def test_top_shap_values_default_top_n_is_5(rf_pipeline, X_transformed, feature_names):
    """top_n padrão é 5."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names)
    for record in results:
        assert len(record) == 5


def test_top_shap_values_feature_names_subset_of_input(rf_pipeline, X_transformed, feature_names):
    """As features retornadas são um subconjunto dos feature_names fornecidos."""
    explainer = build_explainer(rf_pipeline)
    results = top_shap_values(explainer, X_transformed, feature_names, top_n=5)
    feature_set = set(feature_names)
    for record in results:
        assert set(record.keys()).issubset(feature_set)
