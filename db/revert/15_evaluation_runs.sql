-- Revert churn_prediction:15_evaluation_runs from pg

BEGIN;

DROP TABLE IF EXISTS churn.evaluation_run_results;
DROP TABLE IF EXISTS churn.evaluation_runs;

COMMIT;
