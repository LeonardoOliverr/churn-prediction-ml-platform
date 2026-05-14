"""Executa predições em lote para todos os clientes holdout ainda sem predição.

Uso:
    python scripts/predict_holdout_batch.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        --api-key <chave_com_escopo_predict> \\
        [--api-url http://localhost:8000] \\
        [--batch-size 100] \\
        [--dry-run]

Pré-requisitos:
- API em execução (docker compose up ou uvicorn)
- Migration 14_holdout_evaluation aplicada (sqitch deploy)
- Dataset carregado com split atribuído (python scripts/load_ibm_telco.py)
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from sqlalchemy import text

from core.logger import get_logger
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
) -> list[dict]:
    """Envia um lote de clientes para POST /predict/batch e retorna os resultados."""
    response = client.post(
        f"{api_url.rstrip('/')}/predict/batch",
        json={"customers": payloads},
        headers={"x-api-key": api_key},
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
) -> int:
    """Prediz todos os clientes holdout sem predição registrada.

    Retorna o número total de predições enviadas.
    """
    engine = _build_engine()

    with engine.connect() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)
        rows = conn.execute(
            _QUERY_HOLDOUT_WITHOUT_PREDICTIONS,
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

    if dry_run:
        logger.warning(
            "predict_skipped",
            reason="dry_run",
            would_predict=total_candidates,
            batches=-(-total_candidates // batch_size),
        )
        return total_candidates

    batches = [rows[i : i + batch_size] for i in range(0, len(rows), batch_size)]
    total_sent = 0
    total_batches = len(batches)

    with httpx.Client() as client:
        for batch_num, batch in enumerate(batches, start=1):
            payloads = [_row_to_payload(row) for row in batch]
            t0 = time.perf_counter()

            try:
                results = _post_batch(client, api_url, api_key, payloads)
                latency_ms = round((time.perf_counter() - t0) * 1000)
                total_sent += len(results)
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
    )
    return total_sent


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
    )


if __name__ == "__main__":
    main()
