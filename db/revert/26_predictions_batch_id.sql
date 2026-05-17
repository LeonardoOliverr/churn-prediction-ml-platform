-- Revert churn_prediction:26_predictions_batch_id from pg

BEGIN;

DROP INDEX IF EXISTS churn.idx_predictions_eval_batch_id;
ALTER TABLE churn.predictions DROP COLUMN IF EXISTS eval_batch_id;

COMMIT;
