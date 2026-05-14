-- Verify churn_prediction:24_simplify_model_scope on pg

-- scope não existe mais
SELECT 1 / CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM information_schema.columns
WHERE table_schema = 'churn'
  AND table_name   = 'models'
  AND column_name  = 'scope';

-- tenant_id e project_id são NOT NULL
SELECT tenant_id, project_id FROM churn.models LIMIT 1;
