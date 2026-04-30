-- Revert churn_prediction:08_models_unique_constraint from pg

BEGIN;

ALTER TABLE churn.models
    DROP CONSTRAINT models_scope_tenant_project_name_version_key;

ALTER TABLE churn.models
    ADD CONSTRAINT models_name_version_key
    UNIQUE (name, version);

COMMIT;
