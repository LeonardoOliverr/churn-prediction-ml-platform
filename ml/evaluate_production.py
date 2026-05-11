"""Avalia modelos comparando predições com outcomes reais (holdout).

Grava os resultados em churn.evaluation_runs + churn.evaluation_run_results,
preservando snapshot do papel operacional (champion/challenger) e do threshold
no momento da execução.

Uso:
    python ml/evaluate_production.py \\
        --tenant ibm-telco \\
        --project telco-churn-2018 \\
        --since 90d \\
        --fp-cost 100.00 \\
        --fn-cost 2000.00 \\
        [--type monthly|weekly|manual|backtest] \\
        [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone
from itertools import groupby
from typing import Any

from sklearn.metrics import roc_auc_score

from sqlalchemy import text

from ml.core.logger import get_logger
from ml.data.preprocessing import _build_engine, _resolve_project_id, _resolve_tenant_id

logger = get_logger()

# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

_QUERY_EVAL = text("""
    SELECT
        m.id        AS model_id,
        m.name      AS model_name,
        m.version   AS model_version,
        p.churn_pred,
        p.churn_prob,
        p.threshold_used,
        o.churned
    FROM churn.predictions p
    JOIN churn.outcomes o ON o.prediction_id = p.id
    JOIN churn.models   m ON m.id = p.model_id
    WHERE p.tenant_id  = :tenant_id
      AND p.project_id = :project_id
      AND p.requested_at >= :period_start
      AND p.requested_at <  :period_end
    ORDER BY m.name, m.version, p.threshold_used
""")

_QUERY_MISSING_LABELS = text("""
    SELECT m.id AS model_id, COUNT(p.id) AS missing
    FROM churn.predictions p
    JOIN churn.models m ON m.id = p.model_id
    WHERE p.tenant_id  = :tenant_id
      AND p.project_id = :project_id
      AND p.requested_at >= :period_start
      AND p.requested_at <  :period_end
      AND NOT EXISTS (
          SELECT 1 FROM churn.outcomes o WHERE o.prediction_id = p.id
      )
    GROUP BY m.id
""")

_QUERY_ROLE_SNAPSHOT = text("""
    SELECT pmc.role, pmc.traffic_split
    FROM churn.project_model_config pmc
    WHERE pmc.tenant_id = :tenant_id
      AND pmc.model_id  = :model_id
      AND pmc.is_active = TRUE
      AND (pmc.project_id = :project_id OR pmc.project_id IS NULL)
    ORDER BY pmc.project_id NULLS LAST
    LIMIT 1
""")

_QUERY_EXISTING_RUN = text("""
    SELECT id FROM churn.evaluation_runs
    WHERE tenant_id       = :tenant_id
      AND project_id      = :project_id
      AND period_start    = :period_start
      AND period_end      = :period_end
      AND evaluation_type = :evaluation_type
    LIMIT 1
""")

_INSERT_RUN = text("""
    INSERT INTO churn.evaluation_runs
        (tenant_id, project_id, period_start, period_end,
         evaluation_type, fp_cost, fn_cost, triggered_by, status, metadata)
    VALUES
        (:tenant_id, :project_id, :period_start, :period_end,
         :evaluation_type, :fp_cost, :fn_cost, :triggered_by, 'running', :metadata)
    RETURNING id
""")

_UPDATE_RUN_STATUS = text("""
    UPDATE churn.evaluation_runs
       SET status = :status, completed_at = NOW()
     WHERE id = :run_id
""")

_INSERT_RESULT = text("""
    INSERT INTO churn.evaluation_run_results (
        evaluation_run_id, tenant_id, project_id, model_id,
        model_name_snapshot, model_version_snapshot,
        model_role_snapshot, traffic_split_snapshot,
        threshold_used,
        tp, fp, fn, tn,
        precision_score, recall_score, f1_score, roc_auc,
        fp_cost, fn_cost, total_cost,
        evaluated_predictions, missing_actual_labels,
        false_positive_rate, false_negative_rate, specificity,
        high_risk_count, medium_risk_count, low_risk_count,
        promotion_candidate, recommendation_reason,
        cost_per_prediction, traffic_split_pct
    ) VALUES (
        :run_id, :tenant_id, :project_id, :model_id,
        :model_name, :model_version,
        :model_role, :traffic_split,
        :threshold_used,
        :tp, :fp, :fn, :tn,
        :precision, :recall, :f1, :roc_auc,
        :fp_cost, :fn_cost, :total_cost,
        :evaluated_predictions, :missing_actual_labels,
        :false_positive_rate, :false_negative_rate, :specificity,
        :high_risk_count, :medium_risk_count, :low_risk_count,
        :promotion_candidate, :recommendation_reason,
        :cost_per_prediction, :traffic_split_pct
    )
    ON CONFLICT (evaluation_run_id, model_id, threshold_used) DO NOTHING
""")


# ---------------------------------------------------------------------------
# Funções puras — testáveis sem banco
# ---------------------------------------------------------------------------


def _parse_since(since: str) -> int:
    """Converte '90d' para 90 (número de dias inteiro positivo)."""
    if not since.endswith("d"):
        raise ValueError(f"Formato inválido: {since!r}. Use '90d'.")
    days_str = since[:-1]
    if not days_str.isdigit() or int(days_str) <= 0:
        raise ValueError(f"Número de dias inválido: {days_str!r}. Deve ser inteiro positivo.")
    return int(days_str)


def _compute_confusion(rows: list[Any]) -> dict[str, int]:
    """Calcula matriz de confusão a partir de linhas com (churn_pred, churned)."""
    tp = fp = fn = tn = 0
    for row in rows:
        pred   = bool(row.churn_pred)
        actual = bool(row.churned)
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
        elif not pred and actual:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _compute_metrics(cm: dict[str, int]) -> dict[str, float]:
    """Calcula precision, recall e F1 com guard contra divisão por zero."""
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "f1":        round(f1,        4),
    }


def _compute_cost(cm: dict[str, int], fp_cost: float, fn_cost: float) -> float:
    """Calcula custo total: FP * custo_FP + FN * custo_FN."""
    return cm["fp"] * fp_cost + cm["fn"] * fn_cost


def _compute_roc_auc(rows: list[Any]) -> float | None:
    """Calcula ROC-AUC usando as probabilidades brutas de cada predição.

    Retorna None quando há apenas uma classe nos outcomes (AUC indefinido).
    """
    y_true  = [int(bool(row.churned))     for row in rows]
    y_score = [float(row.churn_prob) for row in rows]
    if len(set(y_true)) < 2:
        return None
    return float(round(roc_auc_score(y_true, y_score), 4))


def _compute_derived_rates(cm: dict[str, int]) -> dict[str, float | None]:
    """Calcula taxas derivadas: FPR, FNR e especificidade."""
    fp, tn, fn, tp = cm["fp"], cm["tn"], cm["fn"], cm["tp"]
    fpr  = fp / (fp + tn) if (fp + tn) > 0 else None
    fnr  = fn / (fn + tp) if (fn + tp) > 0 else None
    spec = tn / (tn + fp) if (tn + fp) > 0 else None
    return {
        "false_positive_rate": round(fpr,  4) if fpr  is not None else None,
        "false_negative_rate": round(fnr,  4) if fnr  is not None else None,
        "specificity":         round(spec, 4) if spec is not None else None,
    }


def _compute_risk_segmentation(rows: list[Any]) -> dict[str, int]:
    """Conta predições por faixa de probabilidade de churn."""
    high = medium = low = 0
    for row in rows:
        prob = float(row.churn_prob)
        if prob > 0.7:
            high += 1
        elif prob >= 0.3:
            medium += 1
        else:
            low += 1
    return {"high_risk_count": high, "medium_risk_count": medium, "low_risk_count": low}


def _compute_promotion_recommendation(
    metrics: dict[str, float],
    cost: float,
    total: int,
    role: str,
    champion_metrics: dict[str, float] | None,
    champion_cost: float | None,
    champion_total: int | None,
) -> dict[str, bool | str]:
    """Decide se o modelo deve ser promovido a champion com base nas métricas do run.

    Custo comparado por predição para eliminar viés de volume entre splits de tráfego.
    """
    if role == "champion":
        return {"promotion_candidate": False, "recommendation_reason": "Modelo ativo em produção — referência de comparação."}
    if champion_metrics is None or champion_total is None:
        return {"promotion_candidate": False, "recommendation_reason": "Sem modelo champion disponível para comparação."}

    cost_per_pred          = cost / total          if total          > 0 else float("inf")
    champion_cost_per_pred = champion_cost / champion_total if champion_total > 0 else float("inf")

    better_f1   = metrics["f1"] > (champion_metrics["f1"] or 0.0)
    better_cost = cost_per_pred < champion_cost_per_pred

    if better_f1 and better_cost:
        reason = "Promover — supera o champion em F1 e custo operacional."
    elif better_f1:
        reason = "Promover — F1 superior ao champion."
    elif better_cost:
        reason = "Promover — custo operacional inferior ao champion."
    else:
        reason = "Manter champion — superior em F1 e custo operacional."

    return {"promotion_candidate": better_f1 or better_cost, "recommendation_reason": reason}


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

_HEADER = (
    "Modelo               Role        Ver  Total   TP   FP   FN   TN   Prec   Rec    F1      Custo"
)
_SEP = "=" * 96


def _format_row(
    name: str,
    role: str,
    version: str,
    total: int,
    cm: dict[str, int],
    metrics: dict[str, float],
    cost: float,
) -> str:
    return (
        f"{name:<22} {role:<11} {version:<4} {total:>5}  "
        f"{cm['tp']:>4} {cm['fp']:>4} {cm['fn']:>4} {cm['tn']:>4}  "
        f"{metrics['precision']:.4f} {metrics['recall']:.4f} {metrics['f1']:.4f}  "
        f"R${cost:,.2f}"
    )


def _build_report(
    model_results: list[dict[str, Any]],
    project_slug: str,
    since: str,
    fp_cost: float,
    fn_cost: float,
    run_id: str | None,
) -> str:
    lines = [
        "",
        _SEP,
        f"AVALIAÇÃO HOLDOUT — {project_slug} | Janela: {since}",
        f"FP: R$ {fp_cost:,.2f} | FN: R$ {fn_cost:,.2f}"
        + (f" | run: {run_id}" if run_id else " | dry-run"),
        _SEP,
        _HEADER,
    ]

    best_f1     = max(model_results, key=lambda r: r["metrics"]["f1"])
    best_cost   = min(model_results, key=lambda r: r["cost"])

    for r in model_results:
        lines.append(
            _format_row(
                r["model_name"], r["model_role"], r["model_version"],
                r["total"], r["cm"], r["metrics"], r["cost"],
            )
        )

    lines += [
        _SEP,
        f"Melhor F1   : {best_f1['model_name']} {best_f1['model_version']} ({best_f1['metrics']['f1']:.4f})",
        f"Menor custo : {best_cost['model_name']} {best_cost['model_version']} (R${best_cost['cost']:,.2f})",
        _SEP,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------


def evaluate(
    tenant_slug: str,
    project_slug: str,
    days: int,
    fp_cost: float,
    fn_cost: float,
    evaluation_type: str = "manual",
    triggered_by: str = "manual",
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Avalia todos os modelos com outcomes no período.

    Grava em evaluation_runs + evaluation_run_results.
    Retorna lista de resultados por modelo.
    """
    engine = _build_engine()
    _now         = datetime.now(tz=timezone.utc)
    period_end   = _now.replace(hour=23, minute=59, second=59, microsecond=0)
    period_start = (_now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    with engine.connect() as conn:
        tenant_id  = _resolve_tenant_id(conn, tenant_slug)
        project_id = _resolve_project_id(conn, tenant_id, project_slug)

        # Verificar run existente (idempotência)
        existing = conn.execute(
            _QUERY_EXISTING_RUN,
            {
                "tenant_id":       tenant_id,
                "project_id":      project_id,
                "period_start":    period_start,
                "period_end":      period_end,
                "evaluation_type": evaluation_type,
            },
        ).fetchone()

        if existing and not dry_run:
            logger.warning(
                "evaluation_run_already_exists",
                run_id=str(existing.id),
                hint="Use --type para diferenciar runs no mesmo período.",
            )
            return []

        rows = conn.execute(
            _QUERY_EVAL,
            {"tenant_id": tenant_id, "project_id": project_id,
             "period_start": period_start, "period_end": period_end},
        ).fetchall()

        missing_by_model: dict[str, int] = {
            str(r.model_id): int(r.missing)
            for r in conn.execute(
                _QUERY_MISSING_LABELS,
                {"tenant_id": tenant_id, "project_id": project_id,
                 "period_start": period_start, "period_end": period_end},
            ).fetchall()
        }

    if not rows:
        logger.warning(
            "no_outcomes_found",
            tenant=tenant_slug, project=project_slug, days=days,
        )
        return []

    model_results: list[dict[str, Any]] = []

    # 1º passe: métricas base, taxas derivadas e segmentação de risco
    with engine.connect() as conn:
        for (model_id, model_name, model_version, threshold), group_rows in groupby(
            rows,
            key=lambda r: (r.model_id, r.model_name, r.model_version, r.threshold_used),
        ):
            group   = list(group_rows)
            cm      = _compute_confusion(group)
            metrics = _compute_metrics(cm)
            cost    = _compute_cost(cm, fp_cost, fn_cost)
            roc_auc = _compute_roc_auc(group)
            derived = _compute_derived_rates(cm)
            risk    = _compute_risk_segmentation(group)

            # Snapshot do papel operacional no momento da avaliação
            role_row = conn.execute(
                _QUERY_ROLE_SNAPSHOT,
                {"tenant_id": tenant_id, "project_id": project_id,
                 "model_id": str(model_id)},
            ).fetchone()
            model_role    = role_row.role          if role_row else "unknown"
            traffic_split = float(role_row.traffic_split) if role_row and role_row.traffic_split else None
            total         = len(group)

            model_results.append({
                "model_id":           str(model_id),
                "model_name":         model_name,
                "model_version":      str(model_version),
                "model_role":         model_role,
                "traffic_split":      traffic_split,
                "threshold":          float(threshold),
                "total":              total,
                "cm":                 cm,
                "metrics":            metrics,
                "cost":               cost,
                "roc_auc":            roc_auc,
                "missing_labels":     missing_by_model.get(str(model_id), 0),
                "cost_per_prediction": round(cost / total, 4) if total > 0 else None,
                "traffic_split_pct":  round(traffic_split * 100, 2) if traffic_split is not None else None,
                **derived,
                **risk,
            })

    # 2º passe: recomendação de promoção (requer champion do 1º passe)
    champion_result = next(
        (r for r in model_results if r["model_role"] == "champion"), None
    )
    for r in model_results:
        promotion = _compute_promotion_recommendation(
            metrics=r["metrics"],
            cost=r["cost"],
            total=r["total"],
            role=r["model_role"],
            champion_metrics=champion_result["metrics"] if champion_result else None,
            champion_cost=champion_result["cost"]       if champion_result else None,
            champion_total=champion_result["total"]     if champion_result else None,
        )
        r.update(promotion)

    report = _build_report(
        model_results, project_slug, f"{days}d", fp_cost, fn_cost,
        run_id=None,
    )
    logger.info("evaluation_report", report=report)

    if dry_run:
        logger.warning(
            "evaluation_run_skipped",
            reason="dry_run",
            models=len(model_results),
        )
        return model_results

    # Gravar run + resultados
    run_id: str | None = None
    try:
        with engine.begin() as conn:
            tenant_id  = _resolve_tenant_id(conn, tenant_slug)
            project_id = _resolve_project_id(conn, tenant_id, project_slug)

            run_id = str(
                conn.execute(
                    _INSERT_RUN,
                    {
                        "tenant_id":       tenant_id,
                        "project_id":      project_id,
                        "period_start":    period_start,
                        "period_end":      period_end,
                        "evaluation_type": evaluation_type,
                        "fp_cost":         fp_cost,
                        "fn_cost":         fn_cost,
                        "triggered_by":    triggered_by,
                        "metadata":        None,
                    },
                ).scalar_one()
            )

            for r in model_results:
                conn.execute(
                    _INSERT_RESULT,
                    {
                        "run_id":               run_id,
                        "tenant_id":            tenant_id,
                        "project_id":           project_id,
                        "model_id":             r["model_id"],
                        "model_name":           r["model_name"],
                        "model_version":        r["model_version"],
                        "model_role":           r["model_role"],
                        "traffic_split":        r["traffic_split"],
                        "threshold_used":       r["threshold"],
                        "tp":                   r["cm"]["tp"],
                        "fp":                   r["cm"]["fp"],
                        "fn":                   r["cm"]["fn"],
                        "tn":                   r["cm"]["tn"],
                        "precision":            r["metrics"]["precision"],
                        "recall":               r["metrics"]["recall"],
                        "f1":                   r["metrics"]["f1"],
                        "roc_auc":              r["roc_auc"],
                        "fp_cost":              fp_cost,
                        "fn_cost":              fn_cost,
                        "total_cost":           r["cost"],
                        "evaluated_predictions": r["total"],
                        "missing_actual_labels": r["missing_labels"],
                        "false_positive_rate":  r["false_positive_rate"],
                        "false_negative_rate":  r["false_negative_rate"],
                        "specificity":          r["specificity"],
                        "high_risk_count":      r["high_risk_count"],
                        "medium_risk_count":    r["medium_risk_count"],
                        "low_risk_count":       r["low_risk_count"],
                        "promotion_candidate":  r["promotion_candidate"],
                        "recommendation_reason": r["recommendation_reason"],
                        "cost_per_prediction":  r["cost_per_prediction"],
                        "traffic_split_pct":    r["traffic_split_pct"],
                    },
                )

            conn.execute(
                _UPDATE_RUN_STATUS,
                {"status": "completed", "run_id": run_id},
            )

        logger.info(
            "evaluation_run_completed",
            run_id=run_id,
            models=len(model_results),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

    except Exception:
        if run_id:
            with engine.begin() as conn:
                conn.execute(
                    _UPDATE_RUN_STATUS,
                    {"status": "failed", "run_id": run_id},
                )
        raise

    return model_results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Avalia modelos via holdout e grava em evaluation_runs."
    )
    parser.add_argument("--tenant",   default=None,    help="Slug do tenant.")
    parser.add_argument("--project",  required=True,   help="Slug do projeto.")
    parser.add_argument("--since",    default="90d",   help="Janela de avaliação (ex: 90d).")
    parser.add_argument("--fp-cost",  type=float, required=True, help="Custo unitário de falso positivo.")
    parser.add_argument("--fn-cost",  type=float, required=True, help="Custo unitário de falso negativo.")
    parser.add_argument("--type",     default="manual",
                        choices=["monthly", "weekly", "manual", "backtest"],
                        help="Tipo de avaliação.")
    parser.add_argument("--triggered-by", default="manual", help="Origem da execução.")
    parser.add_argument("--dry-run",  action="store_true", help="Simula sem gravar no banco.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    days = _parse_since(args.since)
    evaluate(
        tenant_slug=args.tenant,
        project_slug=args.project,
        days=days,
        fp_cost=args.fp_cost,
        fn_cost=args.fn_cost,
        evaluation_type=args.type,
        triggered_by=args.triggered_by,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
