-- Revert churn_prediction:28_model_audit_log from pg

BEGIN;

DROP TABLE IF EXISTS churn.model_audit_log;

COMMIT;
