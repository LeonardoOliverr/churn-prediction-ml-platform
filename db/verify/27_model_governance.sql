-- Verify churn_prediction:27_model_governance on pg

-- colunas de governança existem
SELECT approved_by, approved_at, deprecated_at, deprecation_reason,
       successor_model_id, training_row_count, training_churn_rate,
       training_period, tags, notes
FROM churn.models LIMIT 1;

-- índice GIN em tags existe
SELECT 1 FROM pg_indexes
WHERE schemaname = 'churn'
  AND tablename  = 'models'
  AND indexname  = 'idx_models_tags';
