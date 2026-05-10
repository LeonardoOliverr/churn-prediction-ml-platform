-- Revert churn_prediction:16_deprecate_cost_analysis from pg

BEGIN;

DROP VIEW IF EXISTS churn.cost_analysis_v2;

COMMENT ON TABLE churn.cost_analysis IS NULL;

COMMIT;
