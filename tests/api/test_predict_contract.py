"""
[API TEST] Testes de contrato para a futura API FastAPI — POST /predict-churn.

Valida a estrutura esperada do JSON de resposta sem necessidade de servidor
ativo. Quando a API for implementada, estes testes devem ser complementados
com chamadas reais via httpx.AsyncClient ou TestClient do FastAPI.

Contrato esperado de POST /predict-churn:
{
    "customer_id":       string,
    "churn_probability": float  (0.0 a 1.0),
    "risk_level":        "low" | "medium" | "high",
    "prediction":        "churn" | "no_churn",
    "threshold_used":    float,
    "model_version":     string
}
"""

import pytest

from domain.constants import RiskLevel


# ---------------------------------------------------------------------------
# Definição do contrato
# ---------------------------------------------------------------------------

PREDICT_RESPONSE_CONTRACT: dict[str, type] = {
    "customer_id": str,
    "churn_probability": float,
    "risk_level": str,
    "prediction": str,
    "threshold_used": float,
    "model_version": str,
}

VALID_RISK_LEVELS = {r.value for r in RiskLevel}
VALID_PREDICTIONS = {"churn", "no_churn"}


def _validate_predict_response(response: dict) -> None:
    """Valida que o dict de resposta respeita o contrato de /predict-churn.

    Verifica presença de campos, tipos, faixa de probability e
    valores permitidos para risk_level e prediction.
    """
    for field, expected_type in PREDICT_RESPONSE_CONTRACT.items():
        assert field in response, (
            f"Campo obrigatório ausente na resposta: '{field}'"
        )
        assert isinstance(response[field], expected_type), (
            f"Campo '{field}': esperado {expected_type.__name__}, "
            f"recebido {type(response[field]).__name__}"
        )

    assert 0.0 <= response["churn_probability"] <= 1.0, (
        f"churn_probability fora do intervalo [0, 1]: {response['churn_probability']}"
    )
    assert response["risk_level"] in VALID_RISK_LEVELS, (
        f"risk_level inválido: '{response['risk_level']}'. "
        f"Esperado: {VALID_RISK_LEVELS}"
    )
    assert response["prediction"] in VALID_PREDICTIONS, (
        f"prediction inválida: '{response['prediction']}'. "
        f"Esperado: {VALID_PREDICTIONS}"
    )


# ---------------------------------------------------------------------------
# Testes de resposta válida
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_predict_contract_valid_high_risk():
    """[API TEST] Resposta de alto risco satisfaz todos os campos do contrato."""
    response = {
        "customer_id": "abc-123-uuid",
        "churn_probability": 0.82,
        "risk_level": "high",
        "prediction": "churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    _validate_predict_response(response)


@pytest.mark.api
def test_predict_contract_valid_medium_risk():
    """[API TEST] Resposta de risco médio satisfaz todos os campos do contrato."""
    response = {
        "customer_id": "def-456-uuid",
        "churn_probability": 0.63,
        "risk_level": "medium",
        "prediction": "churn",
        "threshold_used": 0.5,
        "model_version": "v2",
    }
    _validate_predict_response(response)


@pytest.mark.api
def test_predict_contract_valid_low_risk():
    """[API TEST] Resposta de baixo risco satisfaz todos os campos do contrato."""
    response = {
        "customer_id": "xyz-789-uuid",
        "churn_probability": 0.12,
        "risk_level": "low",
        "prediction": "no_churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    _validate_predict_response(response)


@pytest.mark.api
def test_predict_contract_boundary_probability_zero():
    """[API TEST] Probabilidade 0.0 é aceita no contrato."""
    response = {
        "customer_id": "zero-prob",
        "churn_probability": 0.0,
        "risk_level": "low",
        "prediction": "no_churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    _validate_predict_response(response)


@pytest.mark.api
def test_predict_contract_boundary_probability_one():
    """[API TEST] Probabilidade 1.0 é aceita no contrato."""
    response = {
        "customer_id": "full-prob",
        "churn_probability": 1.0,
        "risk_level": "high",
        "prediction": "churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    _validate_predict_response(response)


# ---------------------------------------------------------------------------
# Testes de resposta inválida — violações de contrato
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_predict_contract_missing_required_field():
    """[API TEST] Resposta incompleta falha na validação de contrato."""
    incomplete_response = {
        "customer_id": "abc-123",
        "churn_probability": 0.75,
        # risk_level, prediction, threshold_used, model_version ausentes
    }
    with pytest.raises(AssertionError, match="ausente"):
        _validate_predict_response(incomplete_response)


@pytest.mark.api
def test_predict_contract_invalid_probability_above_one():
    """[API TEST] churn_probability > 1.0 viola o contrato."""
    invalid_response = {
        "customer_id": "abc-123",
        "churn_probability": 1.5,
        "risk_level": "high",
        "prediction": "churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    with pytest.raises(AssertionError):
        _validate_predict_response(invalid_response)


@pytest.mark.api
def test_predict_contract_invalid_probability_negative():
    """[API TEST] churn_probability negativa viola o contrato."""
    invalid_response = {
        "customer_id": "abc-123",
        "churn_probability": -0.1,
        "risk_level": "low",
        "prediction": "no_churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    with pytest.raises(AssertionError):
        _validate_predict_response(invalid_response)


@pytest.mark.api
def test_predict_contract_invalid_risk_level():
    """[API TEST] risk_level com valor fora do conjunto permitido viola o contrato."""
    invalid_response = {
        "customer_id": "abc-123",
        "churn_probability": 0.75,
        "risk_level": "critical",
        "prediction": "churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    with pytest.raises(AssertionError, match="risk_level"):
        _validate_predict_response(invalid_response)


@pytest.mark.api
def test_predict_contract_invalid_prediction_value():
    """[API TEST] prediction com valor fora do conjunto permitido viola o contrato."""
    invalid_response = {
        "customer_id": "abc-123",
        "churn_probability": 0.75,
        "risk_level": "high",
        "prediction": "maybe",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    with pytest.raises(AssertionError, match="prediction"):
        _validate_predict_response(invalid_response)


@pytest.mark.api
def test_predict_contract_wrong_field_type():
    """[API TEST] Campo com tipo errado (churn_probability como string) viola o contrato."""
    invalid_response = {
        "customer_id": "abc-123",
        "churn_probability": "0.82",
        "risk_level": "high",
        "prediction": "churn",
        "threshold_used": 0.5,
        "model_version": "v1",
    }
    with pytest.raises(AssertionError):
        _validate_predict_response(invalid_response)
