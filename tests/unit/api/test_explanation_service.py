"""
Testes para src/services/explanation_service.py.

Todos os testes mockam a conexão com o banco e o LLM — sem dependências externas.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.services.explanation_service import get_explanation

_PREDICTION_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
_TENANT_ID = "aabbccdd-0000-0000-0000-000000000001"
_PROJECT_ID = "aabbccdd-0000-0000-0000-000000000002"

_SHAP = {"contract_Month-to-month": 0.31, "monthly_charges": 0.18}

_LLM_CONFIG = {
    "model_id": "gpt-4o-mini",
    "max_tokens": 300,
    "prompt_file": "shap_translation_pt.txt",
    "enabled": True,
    "cost_per_1m_input": 0.150000,
    "cost_per_1m_output": 0.600000,
    "decrypted_api_key": None,
}

_LLM_RESULT = {
    "explanation": "Cliente em risco por contrato mensal.",
    "recommended_actions": "Oferecer contrato anual com desconto.",
    "prompt_tokens": 120,
    "completion_tokens": 60,
}


def _make_prediction_row(**overrides) -> dict:
    base = {
        "customer_id": "CUST-001",
        "shap_values": _SHAP,
        "explanation_text": None,
        "recommended_actions": None,
        "churn_prob": 0.82,
        "project_id": _PROJECT_ID,
    }
    base.update(overrides)
    return base


def _make_db(prediction_row=None, llm_config_row=None):
    """Cria mock de Connection com retornos configuráveis."""
    db = MagicMock()

    def execute_side_effect(query, params=None):
        result = MagicMock()
        sql = str(query)
        if "churn.predictions" in sql:
            result.mappings.return_value.first.return_value = prediction_row
        elif "project_llm_config" in sql:
            result.mappings.return_value.first.return_value = llm_config_row
        else:
            result.mappings.return_value.first.return_value = None
        return result

    db.execute.side_effect = execute_side_effect
    return db


# ---------------------------------------------------------------------------
# 404 — predição não encontrada
# ---------------------------------------------------------------------------


def test_raises_404_when_prediction_not_found():
    """HTTPException 404 quando a predição não existe no tenant."""
    db = _make_db(prediction_row=None)
    with pytest.raises(HTTPException) as exc_info:
        get_explanation(_PREDICTION_ID, _TENANT_ID, db)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Cache — explanation_text já existe
# ---------------------------------------------------------------------------


def test_returns_cached_when_explanation_exists():
    """Se explanation_text já está no banco, retorna cached=True sem chamar LLM."""
    row = _make_prediction_row(
        explanation_text="Texto já existente.",
        recommended_actions="Ação já existente.",
    )
    db = _make_db(prediction_row=row)

    result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.cached is True
    assert result.explanation_text == "Texto já existente."
    assert result.recommended_actions == "Ação já existente."


# ---------------------------------------------------------------------------
# SHAP ausente — retorna null sem chamar LLM
# ---------------------------------------------------------------------------


def test_returns_null_when_shap_missing():
    """explanation_text=None e cached=False quando shap_values é None."""
    row = _make_prediction_row(shap_values=None)
    db = _make_db(prediction_row=row)

    result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.explanation_text is None
    assert result.recommended_actions is None
    assert result.cached is False


# ---------------------------------------------------------------------------
# LLM desabilitado — retorna null sem chamar a API
# ---------------------------------------------------------------------------


def test_returns_null_when_llm_disabled():
    """explanation_text=None quando project_llm_config.enabled=False."""
    disabled_config = {**_LLM_CONFIG, "enabled": False}
    db = _make_db(prediction_row=_make_prediction_row(), llm_config_row=disabled_config)

    result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.explanation_text is None
    assert result.recommended_actions is None
    assert result.cached is False


# ---------------------------------------------------------------------------
# LLM config ausente — retorna null
# ---------------------------------------------------------------------------


def test_returns_null_when_llm_config_missing():
    """explanation_text=None quando não há project_llm_config para o projeto."""
    db = _make_db(prediction_row=_make_prediction_row(), llm_config_row=None)

    result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.explanation_text is None
    assert result.cached is False


# ---------------------------------------------------------------------------
# Geração bem-sucedida — LLM chamado e texto gravado
# ---------------------------------------------------------------------------


def test_generates_and_returns_explanation_and_actions():
    """Chama o LLM, grava no banco e retorna cached=False com ambos os campos."""
    db = _make_db(prediction_row=_make_prediction_row(), llm_config_row=_LLM_CONFIG)

    with patch(
        "src.services.explanation_service.translate_shap_to_text",
        return_value=_LLM_RESULT,
    ):
        result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.explanation_text == "Cliente em risco por contrato mensal."
    assert result.recommended_actions == "Oferecer contrato anual com desconto."
    assert result.cached is False


# ---------------------------------------------------------------------------
# Falha do LLM — retorna null sem levantar exceção
# ---------------------------------------------------------------------------


def test_returns_null_on_llm_error():
    """explanation_text=None quando o LLM levanta exceção — não propaga o erro."""
    db = _make_db(prediction_row=_make_prediction_row(), llm_config_row=_LLM_CONFIG)

    with patch(
        "src.services.explanation_service.translate_shap_to_text",
        side_effect=Exception("API timeout"),
    ):
        result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.explanation_text is None
    assert result.recommended_actions is None
    assert result.cached is False


# ---------------------------------------------------------------------------
# Campos retornados
# ---------------------------------------------------------------------------


def test_response_includes_shap_values():
    """shap_values da predição são incluídos na resposta."""
    row = _make_prediction_row(explanation_text="Texto.", recommended_actions="Ação.")
    db = _make_db(prediction_row=row)

    result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.shap_values == _SHAP


def test_response_prediction_id_matches_input():
    """prediction_id na resposta deve ser o mesmo passado como argumento."""
    row = _make_prediction_row(shap_values=None)
    db = _make_db(prediction_row=row)

    result = get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    assert result.prediction_id == _PREDICTION_ID


# ---------------------------------------------------------------------------
# Cálculo de custo
# ---------------------------------------------------------------------------


def test_calculate_cost_correct():
    """_calculate_cost retorna valor correto dado tokens e preços."""
    from src.services.explanation_service import _calculate_cost

    cost = _calculate_cost(
        prompt_tokens=100_000,
        completion_tokens=50_000,
        cost_per_1m_input=0.150,
        cost_per_1m_output=0.600,
    )
    # (100000 / 1M) * 0.150 + (50000 / 1M) * 0.600 = 0.015 + 0.030 = 0.045
    assert abs(cost - 0.045) < 1e-6


def test_calculate_cost_zero_tokens():
    """Custo zero quando ambos os contadores são zero."""
    from src.services.explanation_service import _calculate_cost

    assert _calculate_cost(0, 0, 0.150, 0.600) == 0.0


# ---------------------------------------------------------------------------
# API key por projeto
# ---------------------------------------------------------------------------


def test_uses_per_project_api_key():
    """translate_shap_to_text é chamado com a api_key descriptografada do projeto."""
    config_with_key = {**_LLM_CONFIG, "decrypted_api_key": "sk-project-key-xyz"}
    db = _make_db(prediction_row=_make_prediction_row(), llm_config_row=config_with_key)

    with patch(
        "src.services.explanation_service.translate_shap_to_text",
        return_value=_LLM_RESULT,
    ) as mock_translate:
        get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    call_kwargs = mock_translate.call_args.kwargs
    assert call_kwargs["api_key"] == "sk-project-key-xyz"


def test_fallback_to_env_key_when_no_project_key():
    """translate_shap_to_text é chamado com api_key=None quando projeto não tem key."""
    db = _make_db(prediction_row=_make_prediction_row(), llm_config_row=_LLM_CONFIG)

    with patch(
        "src.services.explanation_service.translate_shap_to_text",
        return_value=_LLM_RESULT,
    ) as mock_translate:
        get_explanation(_PREDICTION_ID, _TENANT_ID, db)

    call_kwargs = mock_translate.call_args.kwargs
    assert call_kwargs["api_key"] is None
