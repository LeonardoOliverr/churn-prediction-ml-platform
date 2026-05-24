-- Revert churn_prediction:21_cost_model_config from pg

BEGIN;
DROP TABLE IF EXISTS churn.cost_model_config;
COMMIT;
