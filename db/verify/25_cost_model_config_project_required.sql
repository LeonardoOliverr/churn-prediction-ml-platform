-- Verify churn_prediction:25_cost_model_config_project_required on pg

-- project_id é NOT NULL
SELECT project_id FROM churn.cost_model_config LIMIT 1;

-- constraint existe
SELECT 1 FROM information_schema.table_constraints
WHERE table_schema     = 'churn'
  AND table_name       = 'cost_model_config'
  AND constraint_name  = 'cost_model_config_tenant_project_model_key'
  AND constraint_type  = 'UNIQUE';
