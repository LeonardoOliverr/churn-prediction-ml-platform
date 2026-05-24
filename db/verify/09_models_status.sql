-- Verify churn_prediction:09_models_status on pg

BEGIN;

SELECT 1
FROM information_schema.columns
WHERE table_schema = 'churn'
  AND table_name   = 'models'
  AND column_name  = 'status';

ROLLBACK;
