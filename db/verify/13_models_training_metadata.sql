-- Verify churn_prediction:13_models_training_metadata on pg

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name = 'models'
          AND column_name = 'hyperparameters'
          AND udt_name = 'jsonb'
    ) THEN
        RAISE EXCEPTION 'models.hyperparameters JSONB column not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name = 'models'
          AND column_name = 'training_params'
          AND udt_name = 'jsonb'
    ) THEN
        RAISE EXCEPTION 'models.training_params JSONB column not found';
    END IF;
END $$;
