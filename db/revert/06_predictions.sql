-- Revert churn_prediction:06_predictions from pg

BEGIN;

DROP TABLE IF EXISTS churn.predictions;

COMMIT;
