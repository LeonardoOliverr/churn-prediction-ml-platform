"""Tradução de valores SHAP para linguagem de negócio via OpenAI.

O caller (job batch ou service) é responsável por buscar model_id, max_tokens e
prompt_file de churn.project_llm_config e passá-los como argumentos — este módulo
não acessa banco de dados nem variáveis de ambiente além de OPENAI_API_KEY.

Retorno de translate_shap_to_text:
    dict com chaves "explanation" e "recommended_actions" (ambas str).
"""

import json
from pathlib import Path

from openai import OpenAI

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Inicialização lazy — evita falha no startup da API quando OPENAI_API_KEY não está definida."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _load_prompt_template(prompt_file: str) -> str:
    """Carrega o template do prompt a partir do arquivo .txt em prompts/."""
    path = _PROMPTS_DIR / prompt_file
    return path.read_text(encoding="utf-8")


def build_prompt(
    shap_values: dict,
    churn_prob: float,
    risk_level: str,
    prompt_file: str,
) -> str:
    """Constrói o prompt formatado com os valores SHAP e metadados da predição."""
    template = _load_prompt_template(prompt_file)
    factors = "\n".join(
        f"- {feature}: {value:+.3f}"
        for feature, value in sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)
    )
    return template.format(
        factors=factors,
        churn_prob=f"{churn_prob:.0%}",
        risk_level=risk_level,
    )


def translate_shap_to_text(
    shap_values: dict,
    churn_prob: float,
    risk_level: str,
    model_id: str,
    max_tokens: int,
    prompt_file: str,
    api_key: str | None = None,
) -> dict:
    """Chama o LLM e retorna dict com 'explanation' e 'recommended_actions'.

    Levanta openai.OpenAIError em caso de falha na API — o caller decide como tratar.
    Levanta ValueError se a resposta não for JSON válido com as chaves esperadas.
    api_key: chave por projeto — quando None usa o singleton global (_get_client).
    """
    prompt = build_prompt(shap_values, churn_prob, risk_level, prompt_file)
    client = OpenAI(api_key=api_key) if api_key else _get_client()
    response = client.chat.completions.create(
        model=model_id,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)

    if "explanation" not in parsed or "recommended_actions" not in parsed:
        raise ValueError(
            f"Resposta do LLM não contém as chaves esperadas. Recebido: {list(parsed.keys())}"
        )

    return {
        "explanation": parsed["explanation"].strip(),
        "recommended_actions": parsed["recommended_actions"].strip(),
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }
