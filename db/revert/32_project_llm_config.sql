-- Revert churn_prediction:32_project_llm_config from pg

BEGIN;

DROP TABLE IF EXISTS churn.project_llm_config;

COMMIT;
