-- Revert churn_prediction:22_model_performance_result_costs from pg

BEGIN;

DROP VIEW IF EXISTS churn.model_performance;

CREATE VIEW churn.model_performance AS
SELECT
    r.id,
    r.tenant_id,
    r.project_id,
    r.model_id,
    run.fp_cost                 AS false_positive_cost,
    run.fn_cost                 AS false_negative_cost,
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

COMMIT;
