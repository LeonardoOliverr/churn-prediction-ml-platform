-- Revert churn_prediction:31_predictions_shap from pg

BEGIN;

ALTER TABLE churn.predictions DROP COLUMN IF EXISTS shap_values;

COMMIT;
