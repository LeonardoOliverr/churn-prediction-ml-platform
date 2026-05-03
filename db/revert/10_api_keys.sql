-- Revert churn_prediction:10_api_keys from pg

BEGIN;

DROP TABLE IF EXISTS churn.api_keys;

COMMIT;
