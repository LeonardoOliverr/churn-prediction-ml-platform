-- Revert churn_prediction:11_models_status_and_project_config_semantics from pg

BEGIN;

DROP INDEX IF EXISTS churn.uq_project_model_config_active;

ALTER TABLE churn.project_model_config
    DROP CONSTRAINT IF EXISTS project_model_config_environment_check,
    DROP CONSTRAINT IF EXISTS project_model_config_threshold_range_check;

ALTER TABLE churn.models
    DROP CONSTRAINT IF EXISTS models_status_check;

UPDATE churn.models
SET status = CASE status
    WHEN 'approved' THEN 'active'
    WHEN 'trained' THEN 'shadow'
    WHEN 'validated' THEN 'shadow'
    ELSE status
END;

ALTER TABLE churn.models
    ALTER COLUMN status SET DEFAULT 'active',
    ADD CONSTRAINT models_status_check
        CHECK (status IN ('active', 'shadow', 'archived'));

COMMENT ON COLUMN churn.models.status IS
    'Estado operacional do modelo: active (em produção), shadow (paralelo sem impacto no usuário), archived (histórico).';

COMMENT ON COLUMN churn.project_model_config.is_active IS
    'Indica se esta configuração está ativa. Apenas uma configuração ativa por projeto deve ser usada na inferência.';

ALTER TABLE churn.project_model_config
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS environment,
    DROP COLUMN IF EXISTS activation_reason,
    DROP COLUMN IF EXISTS deactivated_at,
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS configured_by;

COMMIT;
