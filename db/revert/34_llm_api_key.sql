-- Revert churn_prediction:34_llm_api_key from pg

BEGIN;

ALTER TABLE churn.project_llm_config
    DROP COLUMN IF EXISTS openai_api_key;

COMMIT;
