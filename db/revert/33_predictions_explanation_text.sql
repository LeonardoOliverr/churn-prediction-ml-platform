-- Revert churn_prediction:33_predictions_explanation_text from pg

BEGIN;

DROP TABLE IF EXISTS churn.llm_usage_log;

ALTER TABLE churn.predictions
    DROP COLUMN IF EXISTS explanation_text,
    DROP COLUMN IF EXISTS recommended_actions;

COMMIT;
