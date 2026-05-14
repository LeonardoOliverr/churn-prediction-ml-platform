"""Configura o modelo de custo real (cltv) para um projeto em churn.cost_model_config.

Uso:
    python scripts/seed_cost_model_config.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        [--cost-model cltv] \\
        [--fp-cost-months 2.0] \\
        [--fp-cost-discount 0.20] \\
        [--fn-cost-cltv-multiplier 1.0] \\
        [--fn-cost-months-multiplier 12.0] \\
        [--notes "descrição opcional"] \\
        [--dry-run]
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

_UPSERT = text("""
    INSERT INTO churn.cost_model_config (
        tenant_id,
        project_id,
        cost_model,
        fp_cost_months,
        fp_cost_discount,
        fn_cost_cltv_multiplier,
        fn_cost_months_multiplier,
        notes
    ) VALUES (
        :tenant_id,
        :project_id,
        :cost_model,
        :fp_cost_months,
        :fp_cost_discount,
        :fn_cost_cltv_multiplier,
        :fn_cost_months_multiplier,
        :notes
    )
    ON CONFLICT (tenant_id, project_id, cost_model)
    DO UPDATE SET
        fp_cost_months            = EXCLUDED.fp_cost_months,
        fp_cost_discount          = EXCLUDED.fp_cost_discount,
        fn_cost_cltv_multiplier   = EXCLUDED.fn_cost_cltv_multiplier,
        fn_cost_months_multiplier = EXCLUDED.fn_cost_months_multiplier,
        notes                     = EXCLUDED.notes,
        is_active                 = TRUE
    RETURNING id, cost_model, is_active
""")


def seed(
    tenant_slug: str,
    project_slug: str,
    cost_model: str,
    fp_cost_months: float,
    fp_cost_discount: float,
    fn_cost_cltv_multiplier: float,
    fn_cost_months_multiplier: float,
    notes: str | None,
    dry_run: bool,
) -> None:
    engine = _build_engine()

    with engine.connect() as conn:
        tenant_id  = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)

    params = {
        "tenant_id":                tenant_id,
        "project_id":               project_id,
        "cost_model":               cost_model,
        "fp_cost_months":           fp_cost_months,
        "fp_cost_discount":         fp_cost_discount,
        "fn_cost_cltv_multiplier":  fn_cost_cltv_multiplier,
        "fn_cost_months_multiplier": fn_cost_months_multiplier,
        "notes":                    notes,
    }

    if dry_run:
        logger.warning(
            "seed_skipped",
            reason="dry_run",
            tenant=tenant_slug,
            project=project_slug,
            cost_model=cost_model,
            params={k: v for k, v in params.items() if k not in ("tenant_id", "project_id")},
        )
        return

    with engine.begin() as conn:
        row = conn.execute(_UPSERT, params).mappings().first()

    logger.info(
        "cost_model_config_seeded",
        id=str(row["id"]),
        cost_model=row["cost_model"],
        tenant=tenant_slug,
        project=project_slug,
        fp_cost_months=fp_cost_months,
        fp_cost_discount=fp_cost_discount,
        fn_cost_cltv_multiplier=fn_cost_cltv_multiplier,
        fn_cost_months_multiplier=fn_cost_months_multiplier,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configura cost_model_config para um projeto."
    )
    parser.add_argument("--tenant",                   required=True,        help="Slug do tenant.")
    parser.add_argument("--project",                  required=True,        help="Slug do projeto.")
    parser.add_argument("--cost-model",               default="cltv",
                        choices=["flat", "cltv", "monthly_charges"],
                        help="Modo de cálculo de custo (padrão: cltv).")
    parser.add_argument("--fp-cost-months",           type=float, default=2.0,
                        help="Meses de mensalidade para custo de FP (padrão: 2.0).")
    parser.add_argument("--fp-cost-discount",         type=float, default=0.20,
                        help="Desconto aplicado sobre a mensalidade no custo de FP (padrão: 0.20).")
    parser.add_argument("--fn-cost-cltv-multiplier",  type=float, default=1.0,
                        help="Fração do CLTV perdida em um FN, modo cltv (padrão: 1.0).")
    parser.add_argument("--fn-cost-months-multiplier", type=float, default=12.0,
                        help="Meses de mensalidade perdidos em um FN, modo monthly_charges (padrão: 12.0).")
    parser.add_argument("--notes",                    default=None,         help="Descrição opcional.")
    parser.add_argument("--dry-run",                  action="store_true",  help="Simula sem gravar.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    seed(
        tenant_slug=args.tenant,
        project_slug=args.project,
        cost_model=args.cost_model,
        fp_cost_months=args.fp_cost_months,
        fp_cost_discount=args.fp_cost_discount,
        fn_cost_cltv_multiplier=args.fn_cost_cltv_multiplier,
        fn_cost_months_multiplier=args.fn_cost_months_multiplier,
        notes=args.notes,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
