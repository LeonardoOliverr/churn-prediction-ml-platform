-- Revert churn_prediction:03_customers from pg

BEGIN;

DROP TABLE IF EXISTS churn.customers;

COMMIT;
