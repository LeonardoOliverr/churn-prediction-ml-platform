"""Gera explanation_text via LLM para predições com shap_values disponíveis.

Uso:
    python scripts/generate_shap_explanations.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        [--batch-id <uuid>]   # processar só um ciclo específico
        [--limit 100]         # processar N predições por execução
        [--dry-run]           # imprimir textos sem gravar no banco

Fluxo:
    1. Busca config LLM do projeto em churn.project_llm_config
    2. Se enabled=FALSE, encerra sem processar
    3. Busca predições com shap_values IS NOT NULL AND explanation_text IS NULL
    4. Deduplica por MD5(shap_values) — mesmo perfil recebe o mesmo texto sem chamada extra
    5. Para cada perfil único, chama o LLM uma vez
    6. Atualiza todas as predições do grupo + insere 1 linha em llm_usage_log por predição
    7. Loga progresso e erros sem interromper o lote

Pré-requisitos:
    - OPENAI_API_KEY definido no ambiente
    - Migrations 32 e 33 aplicadas (sqitch deploy)
    - Predições com shap_values preenchidos (SHAP_ENABLED=true + predict_holdout_batch.py)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text

from core.logger import get_logger
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id
from ml.explainability.llm_translator import translate_shap_to_text

logger = get_logger()

_QUERY_LLM_CONFIG = text("""
    SELECT model_id, max_tokens, prompt_file, enabled,
           cost_per_1m_input, cost_per_1m_output
    FROM   churn.project_llm_config
    WHERE  project_id = :project_id
""")

_QUERY_PENDING = text("""
    SELECT
        id,
        shap_values,
        churn_probability,
        risk_level
    FROM churn.predictions
    WHERE  tenant_id        = :tenant_id
      AND  project_id       = :project_id
      AND  shap_values      IS NOT NULL
      AND  explanation_text IS NULL
      AND  (:batch_id IS NULL OR eval_batch_id = :batch_id::uuid)
    ORDER BY requested_at DESC
    LIMIT  :limit
""")

_UPDATE_EXPLANATION = text("""
    UPDATE churn.predictions
    SET    explanation_text    = :explanation_text,
           recommended_actions = :recommended_actions
    WHERE  id = ANY(:ids)
""")

_INSERT_LLM_LOG = text("""
    INSERT INTO churn.llm_usage_log
        (tenant_id, project_id, prediction_id, model_id,
         prompt_tokens, completion_tokens, cost_usd)
    VALUES
        (:tenant_id, :project_id, :prediction_id, :model_id,
         :prompt_tokens, :completion_tokens, :cost_usd)
""")


def _shap_hash(shap_values: dict) -> str:
    """MD5 dos valores SHAP ordenados — usado para deduplicação."""
    return hashlib.md5(json.dumps(shap_values, sort_keys=True).encode()).hexdigest()


def _calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    cost_per_1m_input: float,
    cost_per_1m_output: float,
) -> float:
    return round(
        (prompt_tokens / 1_000_000) * float(cost_per_1m_input)
        + (completion_tokens / 1_000_000) * float(cost_per_1m_output),
        6,
    )


def run(
    tenant_slug: str,
    project_slug: str,
    batch_id: str | None,
    limit: int,
    dry_run: bool,
) -> None:
    engine = _build_engine()

    with engine.begin() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)

        config_row = conn.execute(_QUERY_LLM_CONFIG, {"project_id": project_id}).mappings().first()
        if config_row is None:
            logger.error(
                "Configuração LLM não encontrada para o projeto '%s'. "
                "Verifique se a migration 32 foi aplicada e o seed executado.",
                project_slug,
            )
            sys.exit(1)

        if not config_row["enabled"]:
            logger.info(
                "Tradução LLM desabilitada para o projeto '%s' (project_llm_config.enabled=FALSE).",
                project_slug,
            )
            return

        model_id = config_row["model_id"]
        max_tokens = config_row["max_tokens"]
        prompt_file = config_row["prompt_file"]
        cost_per_1m_input = config_row["cost_per_1m_input"]
        cost_per_1m_output = config_row["cost_per_1m_output"]

        rows = (
            conn.execute(
                _QUERY_PENDING,
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "batch_id": batch_id,
                    "limit": limit,
                },
            )
            .mappings()
            .all()
        )

    if not rows:
        logger.info("Nenhuma predição pendente de tradução encontrada.")
        return

    logger.info(
        "%d predições pendentes. Modelo: %s | Prompt: %s",
        len(rows),
        model_id,
        prompt_file,
    )

    # Agrupa por hash para evitar chamadas duplicadas ao LLM
    hash_to_ids: dict[str, list] = {}
    hash_to_meta: dict[str, dict] = {}

    for row in rows:
        shap = row["shap_values"]
        h = _shap_hash(shap)
        hash_to_ids.setdefault(h, []).append(row["id"])
        if h not in hash_to_meta:
            hash_to_meta[h] = {
                "shap_values": shap,
                "churn_prob": float(row["churn_probability"]),
                "risk_level": row["risk_level"] or "unknown",
            }

    unique_profiles = len(hash_to_ids)
    logger.info(
        "%d perfis únicos (de %d predições) — %d chamadas LLM necessárias.",
        unique_profiles,
        len(rows),
        unique_profiles,
    )

    ok_count = 0
    err_count = 0
    total_cost = 0.0

    with engine.begin() as conn:
        for h, meta in hash_to_meta.items():
            ids = hash_to_ids[h]
            try:
                llm_result = translate_shap_to_text(
                    shap_values=meta["shap_values"],
                    churn_prob=meta["churn_prob"],
                    risk_level=meta["risk_level"],
                    model_id=model_id,
                    max_tokens=max_tokens,
                    prompt_file=prompt_file,
                )
            except Exception as exc:
                logger.warning(
                    "Erro ao traduzir perfil %s (%d predições): %s",
                    h[:8],
                    len(ids),
                    exc,
                )
                err_count += len(ids)
                continue

            cost_usd = _calculate_cost(
                llm_result["prompt_tokens"],
                llm_result["completion_tokens"],
                cost_per_1m_input,
                cost_per_1m_output,
            )
            total_cost += cost_usd * len(ids)

            if dry_run:
                logger.info(
                    "[DRY-RUN] %d predição(ões) | hash=%s | tokens=%d+%d | custo=US$%.6f\n"
                    "Explicação: %s\nAções: %s",
                    len(ids),
                    h[:8],
                    llm_result["prompt_tokens"],
                    llm_result["completion_tokens"],
                    cost_usd * len(ids),
                    llm_result["explanation"],
                    llm_result["recommended_actions"],
                )
            else:
                conn.execute(
                    _UPDATE_EXPLANATION,
                    {
                        "explanation_text": llm_result["explanation"],
                        "recommended_actions": llm_result["recommended_actions"],
                        "ids": ids,
                    },
                )
                # Registra uma linha de auditoria por predição individual
                for pred_id in ids:
                    conn.execute(
                        _INSERT_LLM_LOG,
                        {
                            "tenant_id": str(tenant_id),
                            "project_id": str(project_id),
                            "prediction_id": str(pred_id),
                            "model_id": model_id,
                            "prompt_tokens": llm_result["prompt_tokens"],
                            "completion_tokens": llm_result["completion_tokens"],
                            "cost_usd": cost_usd,
                        },
                    )

            ok_count += len(ids)

    action = "traduzidas (dry-run)" if dry_run else "atualizadas"
    logger.info(
        "Concluído. %d predições %s | %d com erro | custo estimado US$%.4f.",
        ok_count,
        action,
        err_count,
        total_cost,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera explanation_text via LLM para predições SHAP."
    )
    parser.add_argument("--tenant", default="ibm-telco")
    parser.add_argument("--project", default="telco-churn-2018")
    parser.add_argument("--batch-id", default=None, help="UUID do eval_batch_id (opcional)")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        tenant_slug=args.tenant,
        project_slug=args.project,
        batch_id=args.batch_id,
        limit=args.limit,
        dry_run=args.dry_run,
    )
