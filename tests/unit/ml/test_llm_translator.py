"""
Testes para ml/explainability/llm_translator.py.

Todos os testes mockam o cliente OpenAI — não fazem chamadas reais à API.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ml.explainability.llm_translator import build_prompt, translate_shap_to_text

_SHAP = {
    "contract_Month-to-month": 0.31,
    "monthly_charges": 0.18,
    "tenure_months": -0.09,
}

_PROMPTS_DIR = Path(__file__).parents[3] / "ml" / "explainability" / "prompts"

_VALID_LLM_RESPONSE = {
    "explanation": "Cliente em risco por contrato mensal.",
    "recommended_actions": "Oferecer contrato anual com desconto.",
}

_USAGE = {"prompt_tokens": 120, "completion_tokens": 60}


# ---------------------------------------------------------------------------
# build_prompt — verifica que o template é preenchido corretamente
# ---------------------------------------------------------------------------


def test_build_prompt_contains_factors():
    """O prompt deve conter as features e seus valores."""
    prompt = build_prompt(
        _SHAP, churn_prob=0.82, risk_level="high", prompt_file="shap_translation_pt.txt"
    )

    assert "contract_Month-to-month" in prompt
    assert "+0.310" in prompt
    assert "tenure_months" in prompt
    assert "-0.090" in prompt


def test_build_prompt_contains_churn_prob_formatted():
    """A probabilidade deve aparecer como percentual inteiro."""
    prompt = build_prompt(
        _SHAP, churn_prob=0.82, risk_level="high", prompt_file="shap_translation_pt.txt"
    )
    assert "82%" in prompt


def test_build_prompt_contains_risk_level():
    """O nível de risco deve aparecer no prompt."""
    prompt = build_prompt(
        _SHAP, churn_prob=0.82, risk_level="high", prompt_file="shap_translation_pt.txt"
    )
    assert "high" in prompt


def test_build_prompt_sorted_by_abs_desc():
    """Os fatores devem aparecer ordenados por valor absoluto decrescente."""
    prompt = build_prompt(
        _SHAP, churn_prob=0.5, risk_level="medium", prompt_file="shap_translation_pt.txt"
    )
    idx_contract = prompt.index("contract_Month-to-month")
    idx_monthly = prompt.index("monthly_charges")
    idx_tenure = prompt.index("tenure_months")
    assert idx_contract < idx_monthly < idx_tenure


def test_build_prompt_missing_file_raises():
    """FileNotFoundError quando o arquivo de prompt não existe."""
    with pytest.raises(FileNotFoundError):
        build_prompt(_SHAP, churn_prob=0.5, risk_level="low", prompt_file="nonexistent.txt")


# ---------------------------------------------------------------------------
# translate_shap_to_text — mock da API OpenAI
# ---------------------------------------------------------------------------


def _make_openai_response(
    payload: dict, prompt_tokens: int = 120, completion_tokens: int = 60
) -> MagicMock:
    """Cria mock de resposta OpenAI com o payload JSON e usage."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(payload)
    mock_response.usage.prompt_tokens = prompt_tokens
    mock_response.usage.completion_tokens = completion_tokens
    return mock_response


def test_translate_returns_all_fields():
    """Deve retornar dict com explanation, recommended_actions, prompt_tokens e completion_tokens."""
    with patch("ml.explainability.llm_translator._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = _make_openai_response(
            _VALID_LLM_RESPONSE, prompt_tokens=120, completion_tokens=60
        )
        result = translate_shap_to_text(
            shap_values=_SHAP,
            churn_prob=0.82,
            risk_level="high",
            model_id="gpt-4o-mini",
            max_tokens=300,
            prompt_file="shap_translation_pt.txt",
        )

    assert result["explanation"] == "Cliente em risco por contrato mensal."
    assert result["recommended_actions"] == "Oferecer contrato anual com desconto."
    assert result["prompt_tokens"] == 120
    assert result["completion_tokens"] == 60


def test_translate_strips_whitespace():
    """Os textos retornados não devem ter espaços extras."""
    payload = {
        "explanation": "  Explicação com espaço.  ",
        "recommended_actions": "  Ação com espaço.  ",
    }
    with patch("ml.explainability.llm_translator._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = _make_openai_response(
            payload
        )
        result = translate_shap_to_text(
            shap_values=_SHAP,
            churn_prob=0.5,
            risk_level="medium",
            model_id="gpt-4o-mini",
            max_tokens=300,
            prompt_file="shap_translation_pt.txt",
        )

    assert result["explanation"] == "Explicação com espaço."
    assert result["recommended_actions"] == "Ação com espaço."


def test_translate_calls_correct_model():
    """O model_id passado como argumento deve ser enviado à API."""
    with patch("ml.explainability.llm_translator._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = _make_openai_response(
            _VALID_LLM_RESPONSE
        )
        translate_shap_to_text(
            shap_values=_SHAP,
            churn_prob=0.5,
            risk_level="medium",
            model_id="gpt-4o-mini",
            max_tokens=300,
            prompt_file="shap_translation_pt.txt",
        )

    call_kwargs = mock_client.return_value.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["max_tokens"] == 300
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_translate_raises_on_missing_keys():
    """ValueError quando o LLM retorna JSON sem as chaves esperadas."""
    with patch("ml.explainability.llm_translator._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = _make_openai_response(
            {"texto": "algo"}
        )
        with pytest.raises(ValueError, match="chaves esperadas"):
            translate_shap_to_text(
                shap_values=_SHAP,
                churn_prob=0.5,
                risk_level="low",
                model_id="gpt-4o-mini",
                max_tokens=300,
                prompt_file="shap_translation_pt.txt",
            )


def test_translate_propagates_api_error():
    """Erros da API OpenAI são propagados sem transformação."""
    from openai import OpenAIError

    with patch("ml.explainability.llm_translator._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = OpenAIError(
            "rate_limit_exceeded"
        )
        with pytest.raises(OpenAIError):
            translate_shap_to_text(
                shap_values=_SHAP,
                churn_prob=0.5,
                risk_level="low",
                model_id="gpt-4o-mini",
                max_tokens=300,
                prompt_file="shap_translation_pt.txt",
            )


# ---------------------------------------------------------------------------
# API key por projeto
# ---------------------------------------------------------------------------


def test_translate_uses_custom_api_key():
    """Quando api_key é fornecida, cria OpenAI(api_key=...) e não usa _get_client."""
    with (
        patch("ml.explainability.llm_translator._get_client") as mock_get_client,
        patch("ml.explainability.llm_translator.OpenAI") as mock_openai_cls,
    ):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response(
            _VALID_LLM_RESPONSE
        )
        translate_shap_to_text(
            shap_values=_SHAP,
            churn_prob=0.5,
            risk_level="medium",
            model_id="gpt-4o-mini",
            max_tokens=300,
            prompt_file="shap_translation_pt.txt",
            api_key="sk-custom-key",
        )

    mock_openai_cls.assert_called_once_with(api_key="sk-custom-key")
    mock_get_client.assert_not_called()


# ---------------------------------------------------------------------------
# Arquivo de prompt padrão
# ---------------------------------------------------------------------------


def test_default_prompt_file_exists():
    """O arquivo shap_translation_pt.txt deve existir no diretório de prompts."""
    assert (_PROMPTS_DIR / "shap_translation_pt.txt").exists()


def test_default_prompt_has_required_placeholders():
    """O template padrão deve conter os três placeholders obrigatórios."""
    content = (_PROMPTS_DIR / "shap_translation_pt.txt").read_text(encoding="utf-8")
    assert "{factors}" in content
    assert "{churn_prob}" in content
    assert "{risk_level}" in content


def test_default_prompt_requests_json_with_both_keys():
    """O template padrão deve solicitar JSON com explanation e recommended_actions."""
    content = (_PROMPTS_DIR / "shap_translation_pt.txt").read_text(encoding="utf-8")
    assert "explanation" in content
    assert "recommended_actions" in content
