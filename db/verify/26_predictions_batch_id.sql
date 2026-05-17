-- Verify churn_prediction:26_predictions_batch_id on pg

-- coluna existe e é nullable UUID
SELECT eval_batch_id FROM churn.predictions LIMIT 1;

-- índice parcial existe
SELECT 1 FROM pg_indexes
WHERE schemaname = 'churn'
  AND tablename  = 'predictions'
  AND indexname  = 'idx_predictions_eval_batch_id';
