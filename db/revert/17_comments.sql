-- Revert churn_prediction:17_comments from pg

BEGIN;

COMMENT ON TABLE churn.tenants              IS NULL;
COMMENT ON TABLE churn.projects             IS NULL;
COMMENT ON TABLE churn.customers            IS NULL;
COMMENT ON TABLE churn.models               IS NULL;
COMMENT ON TABLE churn.project_model_config IS NULL;
COMMENT ON TABLE churn.predictions          IS NULL;
COMMENT ON TABLE churn.cost_analysis        IS NULL;

COMMENT ON COLUMN churn.customers.id         IS NULL;
COMMENT ON COLUMN churn.customers.tenant_id  IS NULL;
COMMENT ON COLUMN churn.customers.project_id IS NULL;
COMMENT ON COLUMN churn.customers.created_at IS NULL;

COMMIT;
