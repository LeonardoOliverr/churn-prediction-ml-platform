"""Varre thresholds sobre predições existentes para encontrar o ponto ótimo de custo.

Não requer novas predições — usa churn_prob já gravado em churn.predictions.

Quando churn.cost_model_config está configurado para o projeto (modo cltv ou monthly_charges),
o custo de cada predição é derivado dos atributos reais do cliente (cltv, monthly_charges),
eliminando a distorção de usar um custo flat uniforme para clientes com valores diferentes.

Uso:
    python scripts/optimize_threshold.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        [--fp-cost 100] \\
        [--fn-cost 2000] \\
        [--since 90d] \\
        [--min-threshold 0.05] \\
        [--max-threshold 0.90] \\
        [--step 0.05]

--fp-cost e --fn-cost são opcionais quando cost_model_config está configurado com
modo cltv ou monthly_charges. São obrigatórios apenas no modo flat ou como fallback.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import text

from domain.constants import CostModel
from core.logger import get_logger
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id

logger = get_logger()

_QUERY = text("""
    SELECT
        m.name           AS model_name,
        m.version        AS model_version,
        p.churn_prob,
        o.churned,
        c.cltv,
        c.monthly_charges
    FROM churn.predictions p
    JOIN churn.outcomes  o ON o.prediction_id = p.id
    JOIN churn.models    m ON m.id = p.model_id
    JOIN churn.customers c ON c.customer_id = p.customer_id
                          AND c.project_id  = p.project_id
                          AND c.tenant_id   = p.tenant_id
    WHERE p.tenant_id  = :tenant_id
      AND p.project_id = :project_id
      AND p.requested_at >= :period_start
      AND p.churn_prob IS NOT NULL
    ORDER BY m.name, m.version
""")

_QUERY_COST_CONFIG = text("""
    SELECT
        cost_model,
        fp_cost_flat,
        fn_cost_flat,
        fp_cost_months,
        fp_cost_discount,
        fn_cost_cltv_multiplier,
        fn_cost_months_multiplier
    FROM churn.cost_model_config
    WHERE tenant_id  = :tenant_id
      AND (project_id = :project_id OR project_id IS NULL)
      AND is_active   = TRUE
    ORDER BY project_id NULLS LAST
    LIMIT 1
""")

_SEP    = "=" * 80
_SUBSEP = "-" * 80


def _compute_row_cost(
    row,
    config: dict | None,
    fp_cost_flat: float | None,
    fn_cost_flat: float | None,
) -> tuple[float, float]:
    """Retorna (fp_unit_cost, fn_unit_cost) para um cliente específico.

    Usa o modo configurado em cost_model_config quando disponível;
    cai para os valores flat do CLI como fallback.
    """
    if config is None or config["cost_model"] == CostModel.FLAT:
        return float(fp_cost_flat or 0), float(fn_cost_flat or 0)

    monthly = float(row.monthly_charges or 0)
    fp_cost  = monthly * float(config["fp_cost_months"]) * float(config["fp_cost_discount"])

    if config["cost_model"] == CostModel.CLTV:
        fn_cost = float(row.cltv or 0) * float(config["fn_cost_cltv_multiplier"])
    else:  # monthly_charges
        fn_cost = monthly * float(config["fn_cost_months_multiplier"])

    return fp_cost, fn_cost


def _confusion(y_prob: np.ndarray, y_true: np.ndarray, threshold: float) -> dict:
    pred = y_prob >= threshold
    return {
        "tp": int(( pred &  y_true).sum()),
        "fp": int(( pred & ~y_true).sum()),
        "fn": int((~pred &  y_true).sum()),
        "tn": int((~pred & ~y_true).sum()),
    }


def _metrics(cm: dict) -> dict:
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _bayes_threshold(fp_cost: float, fn_cost: float) -> float:
    """Threshold teórico ótimo baseado na assimetria de custo (válido para custo flat)."""
    return fp_cost / (fp_cost + fn_cost)


def _sweep(
    rows: list,
    config: dict | None,
    fp_cost_flat: float | None,
    fn_cost_flat: float | None,
    thresholds: np.ndarray,
) -> list[dict]:
    """Varre thresholds calculando custo real por cliente quando config não é flat."""
    y_prob = np.array([float(r.churn_prob) for r in rows])
    y_true = np.array([bool(r.churned)     for r in rows], dtype=bool)

    is_flat = config is None or config["cost_model"] == CostModel.FLAT

    if not is_flat:
        costs = [_compute_row_cost(r, config, fp_cost_flat, fn_cost_flat) for r in rows]
        row_fp_costs = np.array([c[0] for c in costs])
        row_fn_costs = np.array([c[1] for c in costs])

    results = []
    for t in thresholds:
        pred = y_prob >= float(t)
        cm = {
            "tp": int(( pred &  y_true).sum()),
            "fp": int(( pred & ~y_true).sum()),
            "fn": int((~pred &  y_true).sum()),
            "tn": int((~pred & ~y_true).sum()),
        }

        if is_flat:
            cost = cm["fp"] * float(fp_cost_flat or 0) + cm["fn"] * float(fn_cost_flat or 0)
        else:
            cost = float(
                row_fp_costs[pred & ~y_true].sum() +
                row_fn_costs[~pred & y_true].sum()
            )

        m = _metrics(cm)
        results.append({
            "threshold": round(float(t), 4),
            "tp": cm["tp"], "fp": cm["fp"], "fn": cm["fn"], "tn": cm["tn"],
            "precision": round(m["precision"], 4),
            "recall":    round(m["recall"],    4),
            "f1":        round(m["f1"],        4),
            "cost":      round(cost, 2),
        })
    return results


def _format_sweep(
    model_name: str,
    model_version: str,
    rows: list[dict],
    config: dict | None,
    fp_cost_flat: float | None,
    fn_cost_flat: float | None,
    current_threshold: float,
) -> str:
    best_cost = min(rows, key=lambda r: r["cost"])
    best_f1   = max(rows, key=lambda r: r["f1"])
    n = rows[0]["tp"] + rows[0]["fp"] + rows[0]["fn"] + rows[0]["tn"]

    cost_model = config["cost_model"] if config else CostModel.FLAT

    if cost_model == CostModel.FLAT:
        fp_c = float(fp_cost_flat or 0)
        fn_c = float(fn_cost_flat or 0)
        bayes_str = f"Bayes ótimo: {_bayes_threshold(fp_c, fn_c):.3f}  |  " if fp_c + fn_c > 0 else ""
        cost_label = f"FP: R${fp_c:,.2f} (flat)  |  FN: R${fn_c:,.2f} (flat)  |  {bayes_str}"
    elif cost_model == CostModel.CLTV:
        cost_label = (
            f"Modelo de custo: {CostModel.CLTV}  |  "
            f"FP = monthly_charges × {config['fp_cost_months']} × {config['fp_cost_discount']}  |  "
            f"FN = cltv × {config['fn_cost_cltv_multiplier']}  |  "
        )
    else:
        cost_label = (
            f"Modelo de custo: {CostModel.MONTHLY_CHARGES}  |  "
            f"FP = monthly_charges × {config['fp_cost_months']} × {config['fp_cost_discount']}  |  "
            f"FN = monthly_charges × {config['fn_cost_months_multiplier']}  |  "
        )

    lines = [
        f"\n{_SEP}",
        f"Modelo: {model_name} {model_version}  |  n={n}",
        f"{cost_label}Atual: {current_threshold:.2f}",
        _SUBSEP,
        f"{'Threshold':>10}  {'TP':>5}  {'FP':>5}  {'FN':>5}  {'TN':>5}  "
        f"{'Prec':>7}  {'Rec':>7}  {'F1':>7}  {'Custo':>14}  {'':4}",
        _SUBSEP,
    ]

    for r in rows:
        flags = []
        if r["threshold"] == best_cost["threshold"]:
            flags.append("★ min-custo")
        if r["threshold"] == best_f1["threshold"] and r["threshold"] != best_cost["threshold"]:
            flags.append("◆ max-F1")
        if abs(r["threshold"] - current_threshold) < 1e-6:
            flags.append("→ atual")

        lines.append(
            f"{r['threshold']:>10.2f}  {r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  {r['tn']:>5}  "
            f"{r['precision']:>7.4f}  {r['recall']:>7.4f}  {r['f1']:>7.4f}  "
            f"R${r['cost']:>12,.2f}  {'  '.join(flags)}"
        )

    lines.append(_SUBSEP)
    lines.append(
        f"  ★ Threshold ótimo por custo : {best_cost['threshold']:.2f}  "
        f"→ R${best_cost['cost']:,.2f}  (FP={best_cost['fp']}, FN={best_cost['fn']})"
    )
    lines.append(
        f"  ◆ Threshold ótimo por F1    : {best_f1['threshold']:.2f}  "
        f"→ F1={best_f1['f1']:.4f}"
    )

    current_rows = [r for r in rows if abs(r["threshold"] - current_threshold) < 1e-6]
    if current_rows and best_cost["threshold"] != current_threshold:
        saving = current_rows[0]["cost"] - best_cost["cost"]
        lines.append(
            f"  Troca para {best_cost['threshold']:.2f} economizaria "
            f"R${saving:,.2f} por ciclo de avaliação."
        )

    lines.append(_SEP)
    return "\n".join(lines)


def optimize(
    tenant_slug: str | None,
    project_slug: str,
    fp_cost: float | None,
    fn_cost: float | None,
    days: int,
    min_threshold: float,
    max_threshold: float,
    step: float,
) -> None:
    engine = _build_engine()
    _now         = datetime.now(tz=timezone.utc)
    period_start = (_now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    thresholds   = np.arange(min_threshold, max_threshold + step / 2, step)

    with engine.connect() as conn:
        tenant_id  = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)

        config_row = conn.execute(
            _QUERY_COST_CONFIG,
            {"tenant_id": tenant_id, "project_id": project_id},
        ).mappings().first()

        config = dict(config_row) if config_row else None

        if config is None or config["cost_model"] == CostModel.FLAT:
            if fp_cost is None or fn_cost is None:
                logger.error(
                    "cost_config_missing",
                    hint="Sem cost_model_config configurado. Forneça --fp-cost e --fn-cost.",
                )
                sys.exit(1)
            if config is None:
                logger.info("cost_model_resolved", mode="flat_cli", fp_cost=fp_cost, fn_cost=fn_cost)
            else:
                logger.info(
                    "cost_model_resolved",
                    mode="flat_db",
                    fp_cost=float(config["fp_cost_flat"] or fp_cost),
                    fn_cost=float(config["fn_cost_flat"] or fn_cost),
                )
        else:
            logger.info("cost_model_resolved", mode=config["cost_model"], project=project_slug)

        all_rows = conn.execute(
            _QUERY,
            {"tenant_id": tenant_id, "project_id": project_id, "period_start": period_start},
        ).fetchall()

    if not all_rows:
        logger.warning("no_outcomes_found", project=project_slug, days=days)
        return

    models: dict[tuple, list] = {}
    for row in all_rows:
        key = (row.model_name, row.model_version)
        models.setdefault(key, []).append(row)

    for (model_name, model_version), rows in models.items():
        sweep_results  = _sweep(rows, config, fp_cost, fn_cost, thresholds)
        best_cost_row  = min(sweep_results, key=lambda r: r["cost"])
        best_f1_row    = max(sweep_results, key=lambda r: r["f1"])
        tabela = _format_sweep(
            model_name, model_version, sweep_results,
            config, fp_cost, fn_cost,
            current_threshold=0.5,
        )
        logger.info(
            "threshold_sweep",
            model=model_name,
            version=model_version,
            n=len(rows),
            cost_model=config["cost_model"] if config else "flat_cli",
            threshold_cost=best_cost_row["threshold"],
            cost_at_optimum=best_cost_row["cost"],
            threshold_f1=best_f1_row["threshold"],
            report=tabela,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Varre thresholds para encontrar o ponto ótimo de custo."
    )
    parser.add_argument("--tenant",        default=None,  help="Slug do tenant.")
    parser.add_argument("--project",       required=True, help="Slug do projeto.")
    parser.add_argument("--fp-cost",       type=float, default=None,
                        help="Custo flat de FP (obrigatório se cost_model_config não estiver configurado).")
    parser.add_argument("--fn-cost",       type=float, default=None,
                        help="Custo flat de FN (obrigatório se cost_model_config não estiver configurado).")
    parser.add_argument("--since",         default="90d", help="Janela de análise (ex: 90d).")
    parser.add_argument("--min-threshold", type=float, default=0.05)
    parser.add_argument("--max-threshold", type=float, default=0.90)
    parser.add_argument("--step",          type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args  = _parse_args()
    since = args.since
    if not since.endswith("d") or not since[:-1].isdigit():
        logger.error("invalid_since_format", value=since, example="90d")
        sys.exit(1)
    days = int(since[:-1])

    optimize(
        tenant_slug=args.tenant,
        project_slug=args.project,
        fp_cost=args.fp_cost,
        fn_cost=args.fn_cost,
        days=days,
        min_threshold=args.min_threshold,
        max_threshold=args.max_threshold,
        step=args.step,
    )


if __name__ == "__main__":
    main()
