-- Deploy churn_prediction:08_models_unique_constraint to pg
-- requires: 04_models

BEGIN;

ALTER TABLE churn.models
    DROP CONSTRAINT models_name_version_key;

ALTER TABLE churn.models
    ADD CONSTRAINT models_scope_tenant_project_name_version_key
    UNIQUE (scope, tenant_id, project_id, name, version);

COMMIT;
