-- Deploy churn_prediction:11_models_status_and_project_config_semantics to pg
-- requires: 05_project_model_config
-- requires: 09_models_status

BEGIN;

ALTER TABLE churn.project_model_config
    ADD COLUMN configured_by     TEXT,
    ADD COLUMN description       TEXT,
    ADD COLUMN deactivated_at    TIMESTAMPTZ,
    ADD COLUMN activation_reason TEXT,
    ADD COLUMN environment       VARCHAR(20) NOT NULL DEFAULT 'production',
    ADD COLUMN created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE churn.project_model_config
    ADD CONSTRAINT project_model_config_threshold_range_check
        CHECK (threshold >= 0 AND threshold <= 1),
    ADD CONSTRAINT project_model_config_environment_check
        CHECK (environment IN ('production', 'staging', 'dev'));

WITH ranked_configs AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY project_id
            ORDER BY configured_at DESC, id DESC
        ) AS position
    FROM churn.project_model_config
    WHERE is_active = TRUE
)
UPDATE churn.project_model_config AS config
SET
    is_active = FALSE,
    deactivated_at = COALESCE(config.deactivated_at, NOW()),
    updated_at = NOW()
FROM ranked_configs AS ranked
WHERE config.id = ranked.id
  AND ranked.position > 1;

CREATE UNIQUE INDEX uq_project_model_config_active
    ON churn.project_model_config (project_id)
    WHERE is_active = TRUE;

ALTER TABLE churn.models
    DROP CONSTRAINT IF EXISTS models_status_check;

UPDATE churn.models
SET status = CASE status
    WHEN 'active' THEN 'approved'
    WHEN 'shadow' THEN 'validated'
    ELSE status
END;

ALTER TABLE churn.models
    ALTER COLUMN status SET DEFAULT 'trained',
    ADD CONSTRAINT models_status_check
        CHECK (status IN ('trained', 'validated', 'approved', 'archived'));

COMMENT ON COLUMN churn.models.status IS
    'Estado técnico do modelo: trained (treinado), validated (validado), approved (elegível para uso em produção), archived (descontinuado). Produção é definida por churn.project_model_config.';

COMMENT ON COLUMN churn.project_model_config.is_active IS
    'Indica se esta configuração é a configuração de produção ativa do projeto. Apenas uma configuração ativa por projeto é permitida.';
COMMENT ON COLUMN churn.project_model_config.configured_by IS
    'Identificador textual do responsável pela configuração, como o sub do JWT de admin.';
COMMENT ON COLUMN churn.project_model_config.description IS
    'Descrição opcional da configuração operacional do modelo.';
COMMENT ON COLUMN churn.project_model_config.deactivated_at IS
    'Data e hora em que a configuração deixou de ser ativa.';
COMMENT ON COLUMN churn.project_model_config.activation_reason IS
    'Motivo operacional para ativação desta configuração.';
COMMENT ON COLUMN churn.project_model_config.environment IS
    'Ambiente da configuração: production, staging ou dev.';
COMMENT ON COLUMN churn.project_model_config.created_at IS
    'Data e hora de criação do registro de configuração.';
COMMENT ON COLUMN churn.project_model_config.updated_at IS
    'Data e hora da última atualização do registro de configuração.';

COMMIT;
