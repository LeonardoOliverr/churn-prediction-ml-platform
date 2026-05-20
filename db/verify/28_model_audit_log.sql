-- Verify churn_prediction:28_model_audit_log on pg

-- tabela existe e tem as colunas esperadas
SELECT id, model_id, tenant_id, project_id, action,
       old_status, new_status, changed_by, reason, metrics_snapshot, created_at
FROM churn.model_audit_log LIMIT 1;

-- índice principal existe
SELECT 1 FROM pg_indexes
WHERE schemaname = 'churn'
  AND tablename  = 'model_audit_log'
  AND indexname  = 'idx_model_audit_log_model_id';
