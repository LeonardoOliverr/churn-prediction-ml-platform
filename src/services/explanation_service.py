"""Serviço de tradução LLM para explicações SHAP on-demand.

Fluxo (lazy computation com cache do banco):
  1. Busca a predição pelo ID dentro do escopo do tenant/projeto da API key
  2. Se explanation_text já existe → retorna com cached=True (sem chamar o LLM)
  3. Se shap_values é NULL → retorna explanation_text=None (SHAP não foi calculado)
  4. Busca project_llm_config — se enabled=False → retorna explanation_text=None
  5. Chama translate_shap_to_text() → grava explanation + llm_usage_log → retorna cached=False
"""

import os

import structlog
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ml.domain.risk import classify_risk
from ml.explainability.llm_translator import translate_shap_to_text
from src.schemas.predict import ExplainResponse

logger = structlog.get_logger()

_LLM_ENCRYPTION_KEY: str = os.environ.get("LLM_ENCRYPTION_KEY", "")

_QUERY_PREDICTION = text("""
    SELECT
        id,
        customer_id,
        shap_values,
        explanation_text,
        recommended_actions,
        churn_prob,
        project_id
    FROM churn.predictions
    WHERE id        = :prediction_id
      AND tenant_id = :tenant_id
""")

_QUERY_LLM_CONFIG = text("""
    SELECT model_id, max_tokens, prompt_file, enabled,
           cost_per_1m_input, cost_per_1m_output,
           CASE
               WHEN openai_api_key IS NOT NULL AND :encryption_key <> ''
               THEN public.pgp_sym_decrypt(openai_api_key, :encryption_key)
               ELSE NULL
           END AS decrypted_api_key
    FROM   churn.project_llm_config
    WHERE  project_id = :project_id
""")

_UPDATE_EXPLANATION = text("""
    UPDATE churn.predictions
    SET    explanation_text    = :explanation_text,
           recommended_actions = :recommended_actions
    WHERE  id = :prediction_id
""")

_INSERT_LLM_LOG = text("""
    INSERT INTO churn.llm_usage_log
        (tenant_id, project_id, prediction_id, model_id,
         prompt_tokens, completion_tokens, cost_usd)
    VALUES
        (:tenant_id, :project_id, :prediction_id, :model_id,
         :prompt_tokens, :completion_tokens, :cost_usd)
""")


def _calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    cost_per_1m_input: float,
    cost_per_1m_output: float,
) -> float:
    """Calcula custo em USD usando preços por milhão de tokens da config do projeto."""
    return round(
        (prompt_tokens / 1_000_000) * float(cost_per_1m_input)
        + (completion_tokens / 1_000_000) * float(cost_per_1m_output),
        6,
    )


def get_explanation(
    prediction_id: str,
    tenant_id: str,
    db: Connection,
) -> ExplainResponse:
    """Retorna ou gera a explicação LLM + recomendações para uma predição específica."""
    row = (
        db.execute(
            _QUERY_PREDICTION,
            {"prediction_id": prediction_id, "tenant_id": tenant_id},
        )
        .mappings()
        .first()
    )

    if row is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Predição '{prediction_id}' não encontrada.",
            },
        )

    customer_id = row["customer_id"]
    shap_values = row["shap_values"]
    explanation_text = row["explanation_text"]
    recommended_actions = row["recommended_actions"]
    project_id = row["project_id"]

    # Cache: explicação já existe no banco
    if explanation_text is not None:
        return ExplainResponse(
            prediction_id=prediction_id,
            customer_id=customer_id,
            explanation_text=explanation_text,
            recommended_actions=recommended_actions,
            shap_values=shap_values,
            cached=True,
        )

    # Sem SHAP → não é possível gerar explicação
    if shap_values is None:
        return ExplainResponse(
            prediction_id=prediction_id,
            customer_id=customer_id,
            explanation_text=None,
            recommended_actions=None,
            shap_values=None,
            cached=False,
        )

    # Busca config do LLM para o projeto
    config = (
        db.execute(
            _QUERY_LLM_CONFIG,
            {"project_id": project_id, "encryption_key": _LLM_ENCRYPTION_KEY},
        )
        .mappings()
        .first()
    )

    if config is None or not config["enabled"]:
        return ExplainResponse(
            prediction_id=prediction_id,
            customer_id=customer_id,
            explanation_text=None,
            recommended_actions=None,
            shap_values=shap_values,
            cached=False,
        )

    # Chama o LLM — falha silenciosa para não interromper o fluxo do cliente
    try:
        churn_prob = float(row["churn_prob"])
        result = translate_shap_to_text(
            shap_values=shap_values,
            churn_prob=churn_prob,
            risk_level=classify_risk(churn_prob).value,
            model_id=config["model_id"],
            max_tokens=config["max_tokens"],
            prompt_file=config["prompt_file"],
            api_key=config["decrypted_api_key"] or None,
        )
    except Exception as exc:
        logger.warning(
            "llm_translation_failed",
            prediction_id=prediction_id,
            error=str(exc),
        )
        return ExplainResponse(
            prediction_id=prediction_id,
            customer_id=customer_id,
            explanation_text=None,
            recommended_actions=None,
            shap_values=shap_values,
            cached=False,
        )

    cost_usd = _calculate_cost(
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        cost_per_1m_input=config["cost_per_1m_input"],
        cost_per_1m_output=config["cost_per_1m_output"],
    )

    db.execute(
        _UPDATE_EXPLANATION,
        {
            "explanation_text": result["explanation"],
            "recommended_actions": result["recommended_actions"],
            "prediction_id": prediction_id,
        },
    )
    db.execute(
        _INSERT_LLM_LOG,
        {
            "tenant_id": tenant_id,
            "project_id": str(project_id),
            "prediction_id": prediction_id,
            "model_id": config["model_id"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "cost_usd": cost_usd,
        },
    )
    db.commit()

    logger.info(
        "llm_explanation_generated",
        prediction_id=prediction_id,
        model_id=config["model_id"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        cost_usd=cost_usd,
    )

    return ExplainResponse(
        prediction_id=prediction_id,
        customer_id=customer_id,
        explanation_text=result["explanation"],
        recommended_actions=result["recommended_actions"],
        shap_values=shap_values,
        cached=False,
    )
