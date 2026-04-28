-- Revert churn_prediction:07_cost_analysis from pg

BEGIN;

DROP TABLE IF EXISTS churn.cost_analysis;

COMMIT;
