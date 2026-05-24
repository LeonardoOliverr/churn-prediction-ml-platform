-- Revert churn_prediction:25_cost_model_config_project_required from pg

BEGIN;

ALTER TABLE churn.cost_model_config
    DROP CONSTRAINT IF EXISTS cost_model_config_tenant_project_model_key;

ALTER TABLE churn.cost_model_config
    ALTER COLUMN project_id DROP NOT NULL;

COMMIT;
