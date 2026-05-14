"""Popula churn.outcomes a partir de predições de clientes holdout sem outcome registrado.

Uso:
    python scripts/seed_outcomes_from_customers.py \
        --tenant ibm-telco \
        --project telco-churn-2018 \
        [--dry-run]

Natureza simulada: confirmed_at = requested_at.
Em produção real, confirmed_at representaria o momento em que o churn
foi efetivamente confirmado (ex.: 30/60/90 dias após a predição).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text

from core.logger import get_logger
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id

logger = get_logger()

_QUERY_CANDIDATES = text("""
    SELECT
        p.id          AS prediction_id,
        p.tenant_id,
        p.project_id,
        p.customer_id,
        p.requested_at,
        c.churn_value
    FROM churn.predictions p
    JOIN churn.customers c
         ON c.project_id  = p.project_id
        AND c.customer_id = p.customer_id
    WHERE p.tenant_id  = :tenant_id
      AND p.project_id = :project_id
      AND c.split      = 'holdout'
      AND NOT EXISTS (
          SELECT 1 FROM churn.outcomes o WHERE o.prediction_id = p.id
      )
""")

_INSERT_OUTCOME = text("""
    INSERT INTO churn.outcomes
        (prediction_id, tenant_id, project_id, customer_id, churned, confirmed_at)
    VALUES
        (:prediction_id, :tenant_id, :project_id, :customer_id, :churned, :confirmed_at)
    ON CONFLICT (prediction_id) DO NOTHING
""")


def seed_outcomes(
    tenant_slug: str,
    project_slug: str,
    dry_run: bool = False,
) -> int:
    """Insere outcomes para predições holdout ainda não avaliadas.

    Retorna o número de outcomes candidatos encontrados.
    """
    engine = _build_engine()

    with engine.connect() as conn:
        tenant_id = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)
        rows = conn.execute(
            _QUERY_CANDIDATES,
            {"tenant_id": tenant_id, "project_id": project_id},
        ).fetchall()

    logger.info(
        "outcomes_candidates_found", count=len(rows), tenant=tenant_slug, project=project_slug
    )

    if not rows:
        logger.info("no_outcomes_to_seed")
        return 0

    if dry_run:
        logger.warning(
            "seed_skipped",
            reason="dry_run",
            count=len(rows),
            sample_customer=rows[0].customer_id if rows else None,
        )
        return len(rows)

    with engine.begin() as conn:
        for row in rows:
            conn.execute(
                _INSERT_OUTCOME,
                {
                    "prediction_id": str(row.prediction_id),
                    "tenant_id": str(row.tenant_id),
                    "project_id": str(row.project_id),
                    "customer_id": row.customer_id,
                    "churned": bool(row.churn_value),
                    "confirmed_at": row.requested_at,
                },
            )

    logger.info("outcomes_seeded", count=len(rows))
    return len(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Popula churn.outcomes a partir de predições de clientes holdout."
    )
    parser.add_argument("--tenant", required=True, help="Slug do tenant.")
    parser.add_argument("--project", required=True, help="Slug do projeto.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar no banco.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    seed_outcomes(
        tenant_slug=args.tenant,
        project_slug=args.project,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
