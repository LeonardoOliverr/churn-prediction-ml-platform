-- Verify churn_prediction:30_update_audit_actions on pg

-- constraint com os novos actions existe
SELECT 1 FROM pg_constraint
WHERE conrelid = 'churn.model_audit_log'::regclass
  AND conname   = 'model_audit_log_action_check';
