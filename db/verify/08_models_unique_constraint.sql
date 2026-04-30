-- Verify churn_prediction:08_models_unique_constraint on pg

BEGIN;

SELECT 1
FROM pg_constraint
WHERE conname = 'models_scope_tenant_project_name_version_key'
  AND conrelid = 'churn.models'::regclass;

ROLLBACK;
