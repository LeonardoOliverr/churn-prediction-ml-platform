-- Revert churn_prediction:01_tenants from pg

BEGIN;

DROP TABLE IF EXISTS churn.tenants;

COMMIT;
