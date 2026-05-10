-- Verify churn_prediction:18_analytics_enhancements on pg

DO $$
DECLARE
    missing_cols TEXT;
    view_count   INTEGER;
BEGIN
    -- Verifica novas colunas em evaluation_run_results
    SELECT string_agg(col, ', ' ORDER BY col)
      INTO missing_cols
      FROM (
          VALUES
              ('false_positive_rate'),
              ('false_negative_rate'),
              ('specificity'),
              ('high_risk_count'),
              ('medium_risk_count'),
              ('low_risk_count'),
              ('promotion_candidate'),
              ('recommendation_reason')
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

    -- Verifica view evaluation_comparison
    SELECT COUNT(*)
      INTO view_count
      FROM information_schema.views
     WHERE table_schema = 'churn'
       AND table_name   = 'evaluation_comparison';

    IF view_count = 0 THEN
        RAISE EXCEPTION 'View churn.evaluation_comparison não encontrada.';
    END IF;

    -- Verifica view model_performance
    SELECT COUNT(*)
      INTO view_count
      FROM information_schema.views
     WHERE table_schema = 'churn'
       AND table_name   = 'model_performance';

    IF view_count = 0 THEN
        RAISE EXCEPTION 'View churn.model_performance não encontrada.';
    END IF;
END $$;
