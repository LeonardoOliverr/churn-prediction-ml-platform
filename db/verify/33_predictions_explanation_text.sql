-- Verify churn_prediction:33_predictions_explanation_text on pg

SELECT explanation_text, recommended_actions FROM churn.predictions LIMIT 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'churn' AND table_name = 'llm_usage_log'
    ) THEN
        RAISE EXCEPTION 'Tabela churn.llm_usage_log não encontrada.';
    END IF;
END $$;
