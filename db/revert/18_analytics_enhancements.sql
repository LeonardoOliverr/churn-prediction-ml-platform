-- Revert churn_prediction:18_analytics_enhancements from pg

BEGIN;

-- Remover views que dependem das colunas novas (ordem importa)
DROP VIEW IF EXISTS churn.model_performance;
DROP VIEW IF EXISTS churn.evaluation_comparison;
DROP VIEW IF EXISTS churn.cost_analysis_v2;

-- Remover colunas adicionadas nesta migration
ALTER TABLE churn.evaluation_run_results
    DROP COLUMN IF EXISTS false_positive_rate,
    DROP COLUMN IF EXISTS false_negative_rate,
    DROP COLUMN IF EXISTS specificity,
    DROP COLUMN IF EXISTS high_risk_count,
    DROP COLUMN IF EXISTS medium_risk_count,
    DROP COLUMN IF EXISTS low_risk_count,
    DROP COLUMN IF EXISTS promotion_candidate,
    DROP COLUMN IF EXISTS recommendation_reason;

-- Restaurar cost_analysis_v2 no estado da migration 16 (sem as novas colunas)
CREATE VIEW churn.cost_analysis_v2 AS
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
