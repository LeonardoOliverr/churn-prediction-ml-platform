-- Revert churn_prediction:24_simplify_model_scope from pg

BEGIN;

ALTER TABLE churn.models
    ALTER COLUMN tenant_id  DROP NOT NULL,
    ALTER COLUMN project_id DROP NOT NULL;

ALTER TABLE churn.models
    ADD COLUMN scope TEXT NOT NULL DEFAULT 'project'
        CHECK (scope IN ('global', 'tenant', 'project'));

COMMIT;
