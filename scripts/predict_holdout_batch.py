"""Executa predições em lote para todos os clientes holdout ainda sem predição.

Uso:
    python scripts/predict_holdout_batch.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        --api-key <chave_com_escopo_predict> \\
        [--api-url http://localhost:8000] \\
        [--batch-size 100] \\
        [--dry-run] \\
        [--force] \\
        [--batch-id <uuid>]

Pré-requisitos:
- API em execução (docker compose up ou uvicorn)
- Migration 14_holdout_evaluation aplicada (sqitch deploy)
- Dataset carregado com split atribuído (python scripts/load_ibm_telco.py)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid as uuid_lib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pandas as pd
from sqlalchemy import text

from core.logger import get_logger
from domain.exceptions import ModelNotFoundError
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id

logger = get_logger()

_BOOL_COLS = ("senior_citizen", "partner", "dependents", "phone_service", "paperless_billing")

_QUERY_HOLDOUT_WITHOUT_PREDICTIONS = text("""
    SELECT
        c.customer_id,
        c.tenure_months,
        c.monthly_charges,
        c.total_charges,
        c.senior_citizen,
        c.partner,
        c.dependents,
        c.phone_service,
        c.paperless_billing,
        c.gender,
        c.multiple_lines,
        c.internet_service,
        c.online_security,
        c.online_backup,
        c.device_protection,
        c.tech_support,
        c.streaming_tv,
        c.streaming_movies,
        c.contract,
        c.payment_method
    FROM churn.customers c
    WHERE c.tenant_id  = :tenant_id
      AND c.project_id = :project_id
      AND c.split      = 'holdout'
      AND NOT EXISTS (
          SELECT 1 FROM churn.predictions p
          WHERE p.tenant_id  = c.tenant_id
            AND p.project_id = c.project_id
            AND p.customer_id = c.customer_id
      )
    ORDER BY c.customer_id
""")

_QUERY_HOLDOUT_ALL = text("""
    SELECT
        c.customer_id,
        c.tenure_months,
        c.monthly_charges,
        c.total_charges,
        c.senior_citizen,
        c.partner,
        c.dependents,
        c.phone_service,
        c.paperless_billing,
        c.gender,
        c.multiple_lines,
        c.internet_service,
        c.online_security,
        c.online_backup,
        c.device_protection,
        c.tech_support,
        c.streaming_tv,
        c.streaming_movies,
        c.contract,
        c.payment_method
    FROM churn.customers c
    WHERE c.tenant_id  = :tenant_id
      AND c.project_id = :project_id
      AND c.split      = 'holdout'
    ORDER BY c.customer_id
""")


_QUERY_CHAMPION_RUN_ID = text("""
    SELECT m.mlflow_run_id
    FROM churn.project_model_config pmc
    JOIN churn.models m ON m.id = pmc.model_id
    WHERE pmc.tenant_id  = :tenant_id
      AND pmc.project_id = :project_id
      AND pmc.environment = 'production'
      AND pmc.is_active   = TRUE
      AND pmc.role        = 'champion'
      AND m.status        = 'approved'
    ORDER BY pmc.configured_at DESC
    LIMIT 1
""")

_UPDATE_SHAP = text("""
    UPDATE churn.predictions
       SET shap_values = :shap_values
     WHERE id = :id
""")


def _load_champion_pipeline(engine, tenant_id: str, project_id: str):
    """Carrega o pipeline sklearn do champion via MLflow para cálculo SHAP local."""
    import mlflow.sklearn

    with engine.connect() as conn:
        run_id = conn.execute(
            _QUERY_CHAMPION_RUN_ID,
            {"tenant_id": tenant_id, "project_id": project_id},
        ).scalar_one_or_none()

    if run_id is None:
        raise ModelNotFoundError(
            f"Nenhum champion ativo encontrado para project_id={project_id}. "
            "Configure um modelo champion antes de calcular SHAP."
        )

    mlflow_uri = f"runs:/{run_id}/model"
    logger.info("loading_champion_for_shap", mlflow_uri=mlflow_uri)
    return mlflow.sklearn.load_model(mlflow_uri)


def _compute_shap_batch(
    pipeline,
    rows: list,
    top_n: int = 5,
) -> list[dict]:
    """Calcula valores SHAP para cada linha e retorna lista de dicts {feature: shap_value}."""
    from ml.core.registry.mlflow import _get_feature_names
    from ml.explainability.shap_explainer import compute_shap_values

    df = pd.DataFrame([_row_to_payload(r) for r in rows]).drop(columns=["customer_id"])
    preprocessor = pipeline.named_steps["preprocessor"]
    X_transformed = preprocessor.transform(df)
    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()

    feature_names = _get_feature_names(pipeline)
    return compute_shap_values(pipeline, X_transformed, feature_names, top_n=top_n)


def _update_shap_in_db(engine, prediction_shap_pairs: list[tuple[str, dict]]) -> None:
    """Atualiza shap_values em churn.predictions para cada (prediction_id, shap_dict)."""
    with engine.begin() as conn:
        for prediction_id, shap_dict in prediction_shap_pairs:
            conn.execute(
                _UPDATE_SHAP,
                {"id": prediction_id, "shap_values": json.dumps(shap_dict)},
            )


def _row_to_payload(row) -> dict:
    """Converte linha do banco em dict compatível com CustomerFeatures."""
    return {
        "customer_id": row.customer_id,
        "tenure_months": float(row.tenure_months or 0),
        "monthly_charges": float(row.monthly_charges or 0),
        "total_charges": float(row.total_charges or 0),
        "senior_citizen": int(bool(row.senior_citizen)),
        "partner": int(bool(row.partner)),
        "dependents": int(bool(row.dependents)),
        "phone_service": int(bool(row.phone_service)),
        "paperless_billing": int(bool(row.paperless_billing)),
        "gender": row.gender or "Male",
        "multiple_lines": row.multiple_lines or "No",
        "internet_service": row.internet_service or "No",
        "online_security": row.online_security or "No",
        "online_backup": row.online_backup or "No",
        "device_protection": row.device_protection or "No",
        "tech_support": row.tech_support or "No",
        "streaming_tv": row.streaming_tv or "No",
        "streaming_movies": row.streaming_movies or "No",
        "contract": row.contract or "Month-to-month",
        "payment_method": row.payment_method or "Electronic check",
    }


def _post_batch(
    client: httpx.Client,
    api_url: str,
    api_key: str,
    payloads: list[dict],
    eval_batch_id: str | None = None,
) -> list[dict]:
    """Envia um lote de clientes para POST /predict/batch e retorna os resultados."""
    headers = {"x-api-key": api_key}
    if eval_batch_id:
        headers["x-eval-batch-id"] = eval_batch_id
    response = client.post(
        f"{api_url.rstrip('/')}/predict/batch",
        json={"customers": payloads},
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["results"]


def predict_holdout_batch(
    tenant_slug: str,
    project_slug: str,
    api_key: str,
    api_url: str = "http://localhost:8000",
    batch_size: int = 100,
    dry_run: bool = False,
    force: bool = False,
    batch_id: str | None = None,
    shap: bool = False,
    shap_top_n: int = 5,
) -> int:
    """Prediz clientes holdout, registrando novas predições no banco.

    Com force=True, reprediz todos os clientes holdout independente de já terem predição —
    útil para gerar novo ciclo de avaliação após mudança de configuração de modelo.

    batch_id identifica este ciclo de avaliação — todas as predições geradas recebem
    o mesmo eval_batch_id, permitindo isolamento posterior em seed/optimize/evaluate.
    Se não fornecido, um UUID é gerado automaticamente.

    Com shap=True, carrega o pipeline champion localmente e calcula valores SHAP após
    o envio dos batches, fazendo UPDATE em churn.predictions.

    Retorna o número total de predições enviadas.
    """
    eval_batch_id = batch_id or str(uuid_lib.uuid4())
    logger.info("eval_batch_started", batch_id=eval_batch_id, shap_enabled=shap)

    engine = _build_engine()
    query = _QUERY_HOLDOUT_ALL if force else _QUERY_HOLDOUT_WITHOUT_PREDICTIONS

    with engine.connect() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)
        rows = conn.execute(
            query,
            {"tenant_id": tenant_id, "project_id": project_id},
        ).fetchall()

    total_candidates = len(rows)
    logger.info(
        "holdout_candidates_found",
        count=total_candidates,
        tenant=tenant_slug,
        project=project_slug,
    )

    if not rows:
        logger.info("no_holdout_customers_to_predict")
        return 0

    if force:
        logger.warning(
            "force_mode_active",
            hint="Repredizendo todos os clientes holdout, incluindo os já previstos.",
            total=total_candidates,
        )

    if dry_run:
        logger.warning(
            "predict_skipped",
            reason="dry_run",
            would_predict=total_candidates,
            batches=-(-total_candidates // batch_size),
            batch_id=eval_batch_id,
        )
        return total_candidates

    batches = [rows[i : i + batch_size] for i in range(0, len(rows), batch_size)]
    total_sent = 0
    total_batches = len(batches)
    all_results: list[dict] = []

    with httpx.Client() as client:
        for batch_num, batch in enumerate(batches, start=1):
            payloads = [_row_to_payload(row) for row in batch]
            t0 = time.perf_counter()

            try:
                results = _post_batch(client, api_url, api_key, payloads, eval_batch_id)
                latency_ms = round((time.perf_counter() - t0) * 1000)
                total_sent += len(results)
                all_results.extend(results)
                logger.info(
                    "batch_sent",
                    batch=batch_num,
                    of=total_batches,
                    size=len(results),
                    total_so_far=total_sent,
                    latency_ms=latency_ms,
                )
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "batch_failed",
                    batch=batch_num,
                    status_code=exc.response.status_code,
                    body=exc.response.text[:200],
                )
                raise

    logger.info(
        "predict_holdout_complete",
        total_sent=total_sent,
        total_candidates=total_candidates,
        batch_id=eval_batch_id,
    )

    if shap and all_results:
        _run_shap_update(engine, tenant_id, project_id, rows, all_results, shap_top_n)

    return total_sent


def _run_shap_update(engine, tenant_id, project_id, rows, api_results, top_n: int) -> None:
    """Calcula SHAP localmente e faz UPDATE em churn.predictions."""
    logger.info("shap_update_started", total=len(rows))

    pipeline = _load_champion_pipeline(engine, tenant_id, project_id)

    # mapeia customer_id → prediction_id a partir das respostas da API
    customer_to_prediction: dict[str, str] = {
        r["customer_id"]: r["prediction_id"] for r in api_results
    }

    # filtra apenas linhas que têm prediction_id (ignora possíveis falhas pontuais)
    valid_rows = [r for r in rows if r.customer_id in customer_to_prediction]
    if not valid_rows:
        logger.warning("shap_update_skipped", reason="no_valid_predictions")
        return

    shap_dicts = _compute_shap_batch(pipeline, valid_rows, top_n=top_n)
    pairs = [
        (customer_to_prediction[row.customer_id], shap_dict)
        for row, shap_dict in zip(valid_rows, shap_dicts, strict=False)
    ]

    _update_shap_in_db(engine, pairs)
    logger.info("shap_update_complete", updated=len(pairs))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predições em lote para clientes holdout sem predição registrada."
    )
    parser.add_argument("--tenant", required=True, help="Slug do tenant.")
    parser.add_argument("--project", required=True, help="Slug do projeto.")
    parser.add_argument(
        "--api-key", default=os.getenv("API_KEY"), help="API key com escopo 'predict'."
    )
    parser.add_argument("--api-url", default="http://localhost:8000", help="URL base da API.")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Clientes por requisição (máx. 100)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem enviar requests.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprediz todos os clientes holdout, mesmo os já previstos. "
        "Use após mudança de configuração de modelo.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="UUID do ciclo de avaliação (eval_batch_id). "
        "Gerado automaticamente se omitido. "
        "Use o valor impresso para filtrar seed/optimize/evaluate.",
    )
    parser.add_argument(
        "--shap",
        action="store_true",
        help="Calcula valores SHAP após o envio dos batches e grava em churn.predictions. "
        "Requer o pacote shap instalado e o champion disponível no MLflow.",
    )
    parser.add_argument(
        "--shap-top-n",
        type=int,
        default=5,
        help="Número de features SHAP a armazenar por predição (padrão: 5).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.api_key:
        logger.error(
            "api_key_missing", hint="Use --api-key ou defina a variável de ambiente API_KEY."
        )
        sys.exit(1)

    if args.batch_size > 100:
        logger.error("batch_size_exceeds_limit", max=100, given=args.batch_size)
        sys.exit(1)

    predict_holdout_batch(
        tenant_slug=args.tenant,
        project_slug=args.project,
        api_key=args.api_key,
        api_url=args.api_url,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        force=args.force,
        batch_id=args.batch_id,
        shap=args.shap,
        shap_top_n=args.shap_top_n,
    )


if __name__ == "__main__":
    main()
