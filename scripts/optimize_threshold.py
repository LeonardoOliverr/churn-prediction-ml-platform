"""Varre thresholds sobre predições existentes para encontrar o ponto ótimo de custo.

Não requer novas predições — usa churn_prob já gravado em churn.predictions.

Uso:
    python scripts/optimize_threshold.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        --fp-cost 100 \\
        --fn-cost 2000 \\
        [--since 90d] \\
        [--min-threshold 0.05] \\
        [--max-threshold 0.90] \\
        [--step 0.05]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import text

from ml.core.logger import get_logger
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id

logger = get_logger()

_QUERY = text("""
    SELECT
        m.name      AS model_name,
        m.version   AS model_version,
        p.churn_prob,
        o.churned
    FROM churn.predictions p
    JOIN churn.outcomes o ON o.prediction_id = p.id
    JOIN churn.models   m ON m.id = p.model_id
    WHERE p.tenant_id  = :tenant_id
      AND p.project_id = :project_id
      AND p.requested_at >= :period_start
      AND p.churn_prob IS NOT NULL
    ORDER BY m.name, m.version
""")

_SEP    = "=" * 80
_SUBSEP = "-" * 80


def _confusion(y_prob: np.ndarray, y_true: np.ndarray, threshold: float) -> dict:
    pred = y_prob >= threshold
    tp = int(( pred &  y_true).sum())
    fp = int(( pred & ~y_true).sum())
    fn = int((~pred &  y_true).sum())
    tn = int((~pred & ~y_true).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _metrics(cm: dict) -> dict:
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _bayes_threshold(fp_cost: float, fn_cost: float) -> float:
    """Threshold teórico ótimo baseado na assimetria de custo."""
    return fp_cost / (fp_cost + fn_cost)


def _sweep(
    y_prob: np.ndarray,
    y_true: np.ndarray,
    fp_cost: float,
    fn_cost: float,
    thresholds: np.ndarray,
) -> list[dict]:
    results = []
    for t in thresholds:
        cm   = _confusion(y_prob, y_true, float(t))
        m    = _metrics(cm)
        cost = cm["fp"] * fp_cost + cm["fn"] * fn_cost
        results.append({
            "threshold": round(float(t), 4),
            "tp": cm["tp"], "fp": cm["fp"], "fn": cm["fn"], "tn": cm["tn"],
            "precision": round(m["precision"], 4),
            "recall":    round(m["recall"],    4),
            "f1":        round(m["f1"],        4),
            "cost":      cost,
        })
    return results


def _print_sweep(
    model_name: str,
    model_version: str,
    rows: list[dict],
    fp_cost: float,
    fn_cost: float,
    current_threshold: float,
) -> None:
    best_cost = min(rows, key=lambda r: r["cost"])
    best_f1   = max(rows, key=lambda r: r["f1"])
    bayes     = _bayes_threshold(fp_cost, fn_cost)

    print(f"\n{_SEP}")
    print(f"Modelo: {model_name} {model_version}  |  n={rows[0]['tp']+rows[0]['fp']+rows[0]['fn']+rows[0]['tn']}")
    print(f"FP: R${fp_cost:,.2f}  |  FN: R${fn_cost:,.2f}  |  Bayes ótimo: {bayes:.3f}  |  Atual: {current_threshold:.2f}")
    print(_SUBSEP)
    print(f"{'Threshold':>10}  {'TP':>5}  {'FP':>5}  {'FN':>5}  {'TN':>5}  "
          f"{'Prec':>7}  {'Rec':>7}  {'F1':>7}  {'Custo':>14}  {'':4}")
    print(_SUBSEP)

    for r in rows:
        flags = []
        if r["threshold"] == best_cost["threshold"]:
            flags.append("★ min-custo")
        if r["threshold"] == best_f1["threshold"] and r["threshold"] != best_cost["threshold"]:
            flags.append("◆ max-F1")
        if abs(r["threshold"] - current_threshold) < 1e-6:
            flags.append("→ atual")

        print(
            f"{r['threshold']:>10.2f}  {r['tp']:>5}  {r['fp']:>5}  {r['fn']:>5}  {r['tn']:>5}  "
            f"{r['precision']:>7.4f}  {r['recall']:>7.4f}  {r['f1']:>7.4f}  "
            f"R${r['cost']:>12,.2f}  {'  '.join(flags)}"
        )

    print(_SUBSEP)
    print(f"  ★ Threshold ótimo por custo : {best_cost['threshold']:.2f}  "
          f"→ R${best_cost['cost']:,.2f}  (FP={best_cost['fp']}, FN={best_cost['fn']})")
    print(f"  ◆ Threshold ótimo por F1    : {best_f1['threshold']:.2f}  "
          f"→ F1={best_f1['f1']:.4f}")

    if best_cost["threshold"] != current_threshold:
        saving = rows[next(i for i, r in enumerate(rows) if abs(r["threshold"] - current_threshold) < 1e-6)]["cost"] - best_cost["cost"]
        print(f"  💡 Troca para {best_cost['threshold']:.2f} economizaria R${saving:,.2f} por ciclo de avaliação.")
    print(_SEP)


def optimize(
    tenant_slug: str | None,
    project_slug: str,
    fp_cost: float,
    fn_cost: float,
    days: int,
    min_threshold: float,
    max_threshold: float,
    step: float,
) -> None:
    engine = _build_engine()
    _now         = datetime.now(tz=timezone.utc)
    period_start = (_now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    thresholds = np.arange(min_threshold, max_threshold + step / 2, step)

    with engine.connect() as conn:
        tenant_id  = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)

        all_rows = conn.execute(
            _QUERY,
            {"tenant_id": tenant_id, "project_id": project_id, "period_start": period_start},
        ).fetchall()

    if not all_rows:
        logger.warning("no_data_found", project=project_slug, days=days)
        print("Nenhuma predição com outcome encontrada no período.")
        return

    # Agrupar por modelo
    models: dict[tuple, list] = {}
    for row in all_rows:
        key = (row.model_name, row.model_version)
        models.setdefault(key, []).append(row)

    for (model_name, model_version), rows in models.items():
        y_prob = np.array([float(r.churn_prob) for r in rows])
        y_true = np.array([bool(r.churned)     for r in rows], dtype=bool)

        # Threshold atual: média dos threshold_used (ou 0.5 se não disponível)
        current_threshold = 0.5

        sweep_results = _sweep(y_prob, y_true, fp_cost, fn_cost, thresholds)
        _print_sweep(model_name, model_version, sweep_results, fp_cost, fn_cost, current_threshold)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Varre thresholds para encontrar o ponto ótimo de custo."
    )
    parser.add_argument("--tenant",        default=None,  help="Slug do tenant.")
    parser.add_argument("--project",       required=True, help="Slug do projeto.")
    parser.add_argument("--fp-cost",       type=float, required=True, help="Custo unitário de FP.")
    parser.add_argument("--fn-cost",       type=float, required=True, help="Custo unitário de FN.")
    parser.add_argument("--since",         default="90d", help="Janela de análise (ex: 90d).")
    parser.add_argument("--min-threshold", type=float, default=0.05)
    parser.add_argument("--max-threshold", type=float, default=0.90)
    parser.add_argument("--step",          type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args  = _parse_args()
    since = args.since
    if not since.endswith("d") or not since[:-1].isdigit():
        print(f"Formato inválido para --since: {since!r}. Use ex: '90d'.")
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
