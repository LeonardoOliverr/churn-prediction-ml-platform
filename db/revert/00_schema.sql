-- Revert churn_prediction:00_schema from pg

BEGIN;

DROP SCHEMA IF EXISTS churn CASCADE;

COMMIT;
