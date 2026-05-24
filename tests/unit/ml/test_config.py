"""
[SCHEMA TEST] Testes de contrato para ml/config.py.

Valida que a configuração de features permanece íntegra — sem sobreposições,
sem data leakage e com as features essenciais do IBM Telco presentes.
"""

import pytest

from ml.config.settings import (
    BOOL_FEATURES,
    CATEGORICAL_FEATURES,
    DROP_COLS,
    NUMERIC_FEATURES,
    TARGET,
)


@pytest.mark.schema
def test_target_column_is_churn_value():
    """[SCHEMA TEST] Confirma que a coluna target é churn_value."""
    assert TARGET == "churn_value"


@pytest.mark.schema
def test_numeric_features_not_empty():
    """[SCHEMA TEST] Lista de features numéricas não pode estar vazia."""
    assert len(NUMERIC_FEATURES) > 0


@pytest.mark.schema
def test_bool_features_not_empty():
    """[SCHEMA TEST] Lista de features booleanas não pode estar vazia."""
    assert len(BOOL_FEATURES) > 0


@pytest.mark.schema
def test_categorical_features_not_empty():
    """[SCHEMA TEST] Lista de features categóricas não pode estar vazia."""
    assert len(CATEGORICAL_FEATURES) > 0


@pytest.mark.schema
def test_drop_cols_not_empty():
    """[SCHEMA TEST] Lista de colunas descartadas não pode estar vazia."""
    assert len(DROP_COLS) > 0


@pytest.mark.schema
def test_target_not_in_any_feature_list():
    """[SCHEMA TEST] TARGET não deve aparecer em nenhuma lista de features (data leakage)."""
    all_features = set(NUMERIC_FEATURES + BOOL_FEATURES + CATEGORICAL_FEATURES)
    assert TARGET not in all_features, (
        f"Data leakage: TARGET '{TARGET}' encontrado nas features de entrada."
    )


@pytest.mark.schema
def test_no_overlap_between_feature_groups():
    """[SCHEMA TEST] Grupos NUMERIC, BOOL e CATEGORICAL não devem ter colunas duplicadas."""
    numeric = set(NUMERIC_FEATURES)
    bool_ = set(BOOL_FEATURES)
    categorical = set(CATEGORICAL_FEATURES)

    assert numeric & bool_ == set(), f"Sobreposição NUMERIC∩BOOL: {numeric & bool_}"
    assert numeric & categorical == set(), (
        f"Sobreposição NUMERIC∩CATEGORICAL: {numeric & categorical}"
    )
    assert bool_ & categorical == set(), f"Sobreposição BOOL∩CATEGORICAL: {bool_ & categorical}"


@pytest.mark.schema
def test_drop_cols_dont_overlap_features():
    """[SCHEMA TEST] Colunas em DROP_COLS não devem aparecer nas features de entrada."""
    all_features = set(NUMERIC_FEATURES + BOOL_FEATURES + CATEGORICAL_FEATURES)
    overlap = all_features & set(DROP_COLS)
    assert overlap == set(), f"Colunas em DROP_COLS também presentes em features: {overlap}"


@pytest.mark.schema
def test_drop_cols_exclude_target():
    """[SCHEMA TEST] TARGET não deve estar em DROP_COLS."""
    assert TARGET not in DROP_COLS, f"'{TARGET}' não deve ser descartado — é a variável resposta."


@pytest.mark.schema
def test_known_numeric_features_present():
    """[SCHEMA TEST] Features numéricas essenciais do IBM Telco devem estar configuradas."""
    required = {"tenure_months", "monthly_charges", "total_charges"}
    missing = required - set(NUMERIC_FEATURES)
    assert missing == set(), f"Features numéricas ausentes: {missing}"


@pytest.mark.schema
def test_known_bool_features_present():
    """[SCHEMA TEST] Features booleanas essenciais do IBM Telco devem estar configuradas."""
    required = {"senior_citizen", "partner"}
    missing = required - set(BOOL_FEATURES)
    assert missing == set(), f"Features booleanas ausentes: {missing}"


@pytest.mark.schema
def test_known_categorical_features_present():
    """[SCHEMA TEST] Features categóricas essenciais do IBM Telco devem estar configuradas."""
    required = {"contract", "payment_method", "internet_service"}
    missing = required - set(CATEGORICAL_FEATURES)
    assert missing == set(), f"Features categóricas ausentes: {missing}"
