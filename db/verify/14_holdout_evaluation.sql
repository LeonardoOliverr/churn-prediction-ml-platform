-- Verify churn_prediction:14_holdout_evaluation on pg

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name   = 'customers'
          AND column_name  = 'split'
    ) THEN
        RAISE EXCEPTION 'customers.split column not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'churn'
          AND table_name   = 'outcomes'
    ) THEN
        RAISE EXCEPTION 'churn.outcomes table not found';
    END IF;
END $$;
