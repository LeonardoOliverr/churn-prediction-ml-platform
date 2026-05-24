-- Deploy churn_prediction:24_simplify_model_scope to pg
-- requires: 23_api_keys_description
--
-- Remove o conceito de modelo global e tenant-scoped.
-- Modelos sempre pertencem a um tenant + project específico.

BEGIN;

-- Garante que não há dados incompatíveis
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM churn.models WHERE scope IN ('global', 'tenant')
    ) THEN
        RAISE EXCEPTION
            'Existem modelos com scope global ou tenant. Migre-os para um projeto antes de prosseguir.';
    END IF;
END $$;

-- Remove scope (sempre foi 'project' na prática)
ALTER TABLE churn.models DROP COLUMN scope;

-- Torna tenant_id e project_id obrigatórios
ALTER TABLE churn.models
    ALTER COLUMN tenant_id  SET NOT NULL,
    ALTER COLUMN project_id SET NOT NULL;

COMMENT ON COLUMN churn.models.tenant_id IS
    'Tenant dono do modelo. Obrigatório — modelos sempre pertencem a um tenant + project.';
COMMENT ON COLUMN churn.models.project_id IS
    'Projeto dono do modelo. Obrigatório — modelos sempre pertencem a um tenant + project.';

COMMIT;
