-- Revert churn_prediction:12_champion_challenger from pg

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM churn.project_model_config
        WHERE project_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Cannot revert 12_champion_challenger while tenant-level model configs exist';
    END IF;
END $$;

UPDATE churn.project_model_config
SET
    is_active = FALSE,
    deactivated_at = COALESCE(deactivated_at, NOW()),
    updated_at = NOW()
WHERE is_active = TRUE
  AND role = 'challenger';

DROP INDEX IF EXISTS churn.uq_project_model_config_active_challenger;
DROP INDEX IF EXISTS churn.uq_project_model_config_active_champion;
DROP INDEX IF EXISTS churn.uq_project_model_config_scope_model;

ALTER TABLE churn.project_model_config
    DROP CONSTRAINT IF EXISTS project_model_config_traffic_split_range_check,
    DROP CONSTRAINT IF EXISTS project_model_config_role_check;

ALTER TABLE churn.project_model_config
    ALTER COLUMN project_id SET NOT NULL;

ALTER TABLE churn.project_model_config
    ADD CONSTRAINT project_model_config_project_id_model_id_key
        UNIQUE (project_id, model_id);

ALTER TABLE churn.project_model_config
    DROP COLUMN IF EXISTS traffic_split,
    DROP COLUMN IF EXISTS role;

CREATE UNIQUE INDEX uq_project_model_config_active
    ON churn.project_model_config (project_id)
    WHERE is_active = TRUE;

COMMENT ON COLUMN churn.project_model_config.project_id IS
    'Projeto ao qual a configuracao pertence.';

COMMIT;
