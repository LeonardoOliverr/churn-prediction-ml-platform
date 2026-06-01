-- Verify churn_prediction:32_project_llm_config on pg

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'churn' AND table_name = 'project_llm_config'
    ) THEN
        RAISE EXCEPTION 'Tabela churn.project_llm_config não encontrada.';
    END IF;
END $$;
