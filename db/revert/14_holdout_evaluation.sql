-- Revert churn_prediction:14_holdout_evaluation from pg

BEGIN;

DROP TABLE IF EXISTS churn.outcomes;

ALTER TABLE churn.customers
    DROP COLUMN IF EXISTS split;

COMMIT;
