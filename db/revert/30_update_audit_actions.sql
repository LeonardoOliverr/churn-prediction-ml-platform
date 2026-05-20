-- Revert churn_prediction:30_update_audit_actions from pg

BEGIN;

ALTER TABLE churn.model_audit_log DROP CONSTRAINT IF EXISTS model_audit_log_action_check;

ALTER TABLE churn.model_audit_log
    ADD CONSTRAINT model_audit_log_action_check
        CHECK (action IN (
            'registered',
            'approved',
            'configured',
            'promoted',
            'deprecated',
            'rejected'
        ));

COMMIT;
