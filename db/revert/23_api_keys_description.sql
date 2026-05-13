-- Revert churn_prediction:23_api_keys_description from pg

BEGIN;

ALTER TABLE churn.api_keys DROP COLUMN IF EXISTS description;

COMMIT;
