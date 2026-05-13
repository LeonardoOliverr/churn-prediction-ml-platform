-- Deploy churn_prediction:22_model_performance_result_costs to pg
-- requires: 21_cost_model_config
--
-- Atualiza model_performance para usar fp_cost/fn_cost de evaluation_run_results
-- (custos médios efetivos por predição) em vez de evaluation_runs (valores CLI).
-- Necessário após a migration 21: com custo cltv, os valores CLI passam a ser 0
-- e os custos reais ficam em evaluation_run_results.fp_cost e fn_cost.

BEGIN;

DROP VIEW churn.model_performance;

CREATE VIEW churn.model_performance AS
SELECT
    r.id,
    r.tenant_id,
    r.project_id,
    r.model_id,
    r.fp_cost                   AS false_positive_cost,
    r.fn_cost                   AS false_negative_cost,
    r.total_cost,
    r.threshold_used,
    r.tp,
    r.fp,
    r.fn,
    r.tn,
    r.precision_score,
    r.recall_score,
    r.f1_score,
    r.roc_auc,
    r.false_positive_rate,
    r.false_negative_rate,
    r.specificity,
    r.high_risk_count,
    r.medium_risk_count,
    r.low_risk_count,
    r.promotion_candidate,
    r.recommendation_reason,
    r.evaluated_predictions     AS total_predictions,
    run.period_start,
    run.period_end,
    run.evaluation_type,
    r.model_role_snapshot,
    r.model_name_snapshot,
    r.model_version_snapshot,
    r.created_at                AS evaluated_at,
    run.id                      AS evaluation_run_id
FROM churn.evaluation_run_results r
JOIN churn.evaluation_runs run ON run.id = r.evaluation_run_id;

COMMENT ON VIEW churn.model_performance IS
    'View consolidada sobre evaluation_run_results. '
    'false_positive_cost e false_negative_cost vêm de evaluation_run_results.fp_cost/fn_cost '
    '(custo médio efetivo por predição no run — flat ou média ponderada no modo cltv/monthly_charges), '
    'não mais de evaluation_runs.fp_cost/fn_cost (valores CLI que podem ser placeholder).';

GRANT SELECT ON churn.model_performance TO grafana_readonly;

COMMIT;
