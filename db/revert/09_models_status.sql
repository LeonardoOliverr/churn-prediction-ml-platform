-- Revert churn_prediction:09_models_status from pg

BEGIN;

ALTER TABLE churn.models DROP COLUMN status;

COMMIT;
