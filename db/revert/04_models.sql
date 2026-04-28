-- Revert churn_prediction:04_models from pg

BEGIN;

DROP TABLE IF EXISTS churn.models;

COMMIT;
