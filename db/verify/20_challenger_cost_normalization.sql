-- Verify churn_prediction:20_challenger_cost_normalization on pg

DO $$
DECLARE
    missing_cols TEXT;
BEGIN
    SELECT string_agg(col, ', ' ORDER BY col)
      INTO missing_cols
      FROM (
          VALUES
              ('cost_per_prediction'),
              ('traffic_split_pct')
      ) AS expected(col)
     WHERE NOT EXISTS (
         SELECT 1
           FROM information_schema.columns
          WHERE table_schema = 'churn'
            AND table_name   = 'evaluation_run_results'
            AND column_name  = expected.col
     );

    IF missing_cols IS NOT NULL THEN
        RAISE EXCEPTION 'Colunas ausentes em evaluation_run_results: %', missing_cols;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'churn' AND table_name = 'evaluation_comparison'
    ) THEN
        RAISE EXCEPTION 'View churn.evaluation_comparison não encontrada.';
    END IF;
END $$;
