-- Deploy churn_prediction:25_cost_model_config_project_required to pg
-- requires: 24_simplify_model_scope
--
-- Remove o fallback de tenant-level em cost_model_config.
-- Configurações de custo sempre pertencem a um projeto específico.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM churn.cost_model_config WHERE project_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Existem cost_model_config sem project_id. Associe-os a um projeto antes de prosseguir.';
    END IF;
END $$;

ALTER TABLE churn.cost_model_config
    ALTER COLUMN project_id SET NOT NULL;

-- Recria UNIQUE explícito (antes NULL != NULL permitia duplicatas)
ALTER TABLE churn.cost_model_config
    DROP CONSTRAINT IF EXISTS cost_model_config_tenant_id_project_id_cost_model_key;

ALTER TABLE churn.cost_model_config
    ADD CONSTRAINT cost_model_config_tenant_project_model_key
        UNIQUE (tenant_id, project_id, cost_model);

COMMENT ON COLUMN churn.cost_model_config.project_id IS
    'Projeto ao qual esta configuração de custo pertence. Obrigatório — sem fallback de tenant.';

COMMIT;
