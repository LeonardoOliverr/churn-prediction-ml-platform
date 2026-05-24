-- Verify churn_prediction:29_rename_model_statuses on pg

-- constraint com os novos valores existe
SELECT 1 FROM pg_constraint
WHERE conrelid = 'churn.models'::regclass
  AND conname   = 'models_status_check';

-- nenhuma linha com status legado
SELECT COUNT(*) FROM churn.models
WHERE status NOT IN ('candidate', 'approved', 'rejected', 'retired');
