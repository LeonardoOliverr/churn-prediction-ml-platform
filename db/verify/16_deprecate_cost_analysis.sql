-- Verify churn_prediction:16_deprecate_cost_analysis on pg
-- Verifica o COMMENT DEPRECATED em cost_analysis (a view foi renomeada na migration 18)

DO $$
DECLARE
    cmt TEXT;
BEGIN
    SELECT obj_description('churn.cost_analysis'::regclass)
      INTO cmt;

    IF cmt IS NULL OR cmt NOT LIKE '%DEPRECATED%' THEN
        RAISE EXCEPTION
            'COMMENT DEPRECATED ausente em churn.cost_analysis. Migration 16 pode não ter sido aplicada.';
    END IF;
END $$;
