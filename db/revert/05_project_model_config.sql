-- Revert churn_prediction:05_project_model_config from pg

BEGIN;

DROP TABLE IF EXISTS churn.project_model_config;

COMMIT;
