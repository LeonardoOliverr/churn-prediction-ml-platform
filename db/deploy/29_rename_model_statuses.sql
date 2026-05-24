-- Deploy churn_prediction:29_rename_model_statuses to pg
-- requires: 28_model_audit_log

BEGIN;

ALTER TABLE churn.models DROP CONSTRAINT models_status_check;

UPDATE churn.models SET status = 'candidate' WHERE status IN ('trained', 'validated');
UPDATE churn.models SET status = 'retired'   WHERE status = 'archived';

ALTER TABLE churn.models
    ALTER COLUMN status SET DEFAULT 'candidate',
    ADD CONSTRAINT models_status_check
        CHECK (status IN ('candidate', 'approved', 'rejected', 'retired'));

COMMENT ON COLUMN churn.models.status IS
    'Estado de governança do modelo: candidate (recém treinado, aguardando revisão humana), '
    'approved (aprovado para uso em produção), rejected (reprovado na revisão), '
    'retired (descontinuado). Papel de deployment definido por churn.project_model_config.';

COMMIT;
