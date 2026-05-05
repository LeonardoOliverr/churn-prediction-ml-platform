-- Verify churn_prediction:11_models_status_and_project_config_semantics on pg

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.check_constraints
        WHERE constraint_schema = 'churn'
          AND constraint_name = 'models_status_check'
    ) THEN
        RAISE EXCEPTION 'models_status_check constraint not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'churn'
          AND tablename = 'project_model_config'
          AND indexname IN (
              'uq_project_model_config_active',
              'uq_project_model_config_active_champion'
          )
    ) THEN
        RAISE EXCEPTION 'active project_model_config unique index not found';
    END IF;
END
$$;

SELECT configured_by, description, deactivated_at, activation_reason, environment, created_at, updated_at
FROM churn.project_model_config
WHERE FALSE;

ROLLBACK;
