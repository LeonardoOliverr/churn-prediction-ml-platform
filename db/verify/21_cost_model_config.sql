-- Verify churn_prediction:21_cost_model_config on pg

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'churn' AND table_name = 'cost_model_config'
    ) THEN
        RAISE EXCEPTION 'Tabela churn.cost_model_config não encontrada.';
    END IF;
END $$;
