-- Verify churn_prediction:12_champion_challenger on pg

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name = 'project_model_config'
          AND column_name = 'role'
    ) THEN
        RAISE EXCEPTION 'project_model_config.role column not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name = 'project_model_config'
          AND column_name = 'traffic_split'
    ) THEN
        RAISE EXCEPTION 'project_model_config.traffic_split column not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name = 'project_model_config'
          AND column_name = 'project_id'
          AND is_nullable = 'YES'
    ) THEN
        RAISE EXCEPTION 'project_model_config.project_id must be nullable';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'churn'
          AND tablename = 'project_model_config'
          AND indexname = 'uq_project_model_config_scope_model'
          AND indexdef ILIKE '%NULLS NOT DISTINCT%'
    ) THEN
        RAISE EXCEPTION 'uq_project_model_config_scope_model index not found or not NULLS NOT DISTINCT';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'churn'
          AND tablename = 'project_model_config'
          AND indexname = 'uq_project_model_config_active_champion'
          AND indexdef ILIKE '%tenant_id%'
          AND indexdef ILIKE '%project_id%'
          AND indexdef ILIKE '%NULLS NOT DISTINCT%'
    ) THEN
        RAISE EXCEPTION 'tenant/project active champion index not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'churn'
          AND tablename = 'project_model_config'
          AND indexname = 'uq_project_model_config_active_challenger'
          AND indexdef ILIKE '%tenant_id%'
          AND indexdef ILIKE '%project_id%'
          AND indexdef ILIKE '%NULLS NOT DISTINCT%'
    ) THEN
        RAISE EXCEPTION 'tenant/project active challenger index not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.check_constraints
        WHERE constraint_schema = 'churn'
          AND constraint_name = 'project_model_config_role_check'
    ) THEN
        RAISE EXCEPTION 'project_model_config_role_check constraint not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.check_constraints
        WHERE constraint_schema = 'churn'
          AND constraint_name = 'project_model_config_traffic_split_range_check'
    ) THEN
        RAISE EXCEPTION 'project_model_config_traffic_split_range_check constraint not found';
    END IF;
END $$;
