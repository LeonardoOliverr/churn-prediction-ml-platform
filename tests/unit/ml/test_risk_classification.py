"""
Testes unitários para ml/risk.py — função classify_risk().

Cobre todos os limites de threshold, casos extremos e tratamento de
probabilidades inválidas.
"""

import pytest

from ml.core.risk import classify_risk


# ---------------------------------------------------------------------------
# Risco alto (>= threshold_high)
# ---------------------------------------------------------------------------


def test_high_risk_at_threshold():
    """Probabilidade exatamente no limiar alto retorna 'high'."""
    assert classify_risk(0.8) == "high"


def test_high_risk_above_threshold():
    """Probabilidade acima do limiar alto retorna 'high'."""
    assert classify_risk(0.9) == "high"
    assert classify_risk(1.0) == "high"


# ---------------------------------------------------------------------------
# Risco médio (>= threshold_low e < threshold_high)
# ---------------------------------------------------------------------------


def test_medium_risk_at_lower_threshold():
    """Probabilidade exatamente no limiar baixo retorna 'medium'."""
    assert classify_risk(0.4) == "medium"


def test_medium_risk_between_thresholds():
    """Probabilidade entre os limiares retorna 'medium'."""
    assert classify_risk(0.5) == "medium"
    assert classify_risk(0.6) == "medium"
    assert classify_risk(0.79) == "medium"


# ---------------------------------------------------------------------------
# Risco baixo (< threshold_low)
# ---------------------------------------------------------------------------


def test_low_risk_below_threshold():
    """Probabilidade abaixo do limiar baixo retorna 'low'."""
    assert classify_risk(0.3) == "low"
    assert classify_risk(0.1) == "low"
    assert classify_risk(0.39) == "low"


def test_low_risk_at_zero():
    """Probabilidade zero retorna 'low'."""
    assert classify_risk(0.0) == "low"


# ---------------------------------------------------------------------------
# Tratamento de probabilidades inválidas
# ---------------------------------------------------------------------------


def test_probability_below_zero_raises_value_error():
    """Probabilidade negativa lança ValueError."""
    with pytest.raises(ValueError, match="0.0 e 1.0"):
        classify_risk(-0.1)


def test_probability_above_one_raises_value_error():
    """Probabilidade acima de 1.0 lança ValueError."""
    with pytest.raises(ValueError, match="0.0 e 1.0"):
        classify_risk(1.1)


def test_large_negative_probability_raises_value_error():
    """Probabilidade muito negativa lança ValueError."""
    with pytest.raises(ValueError):
        classify_risk(-100.0)


def test_large_positive_probability_raises_value_error():
    """Probabilidade muito acima de 1 lança ValueError."""
    with pytest.raises(ValueError):
        classify_risk(99.0)


# ---------------------------------------------------------------------------
# Thresholds customizados
# ---------------------------------------------------------------------------


def test_custom_thresholds_high():
    """Threshold customizado: 0.7 com high em 0.6 retorna 'high'."""
    assert classify_risk(0.7, threshold_low=0.3, threshold_high=0.6) == "high"


def test_custom_thresholds_medium():
    """Threshold customizado: 0.4 com low=0.3, high=0.6 retorna 'medium'."""
    assert classify_risk(0.4, threshold_low=0.3, threshold_high=0.6) == "medium"


def test_custom_thresholds_low():
    """Threshold customizado: 0.2 com low=0.3, high=0.6 retorna 'low'."""
    assert classify_risk(0.2, threshold_low=0.3, threshold_high=0.6) == "low"


def test_return_type_is_string():
    """classify_risk() sempre retorna uma string."""
    for prob in [0.0, 0.4, 0.8, 1.0]:
        result = classify_risk(prob)
        assert isinstance(result, str), f"Retorno não é string para probability={prob}"


def test_valid_return_values_only():
    """Todos os valores retornados estão no conjunto {'low', 'medium', 'high'}."""
    valid = {"low", "medium", "high"}
    for prob in [0.0, 0.2, 0.39, 0.4, 0.6, 0.79, 0.8, 1.0]:
        assert classify_risk(prob) in valid
