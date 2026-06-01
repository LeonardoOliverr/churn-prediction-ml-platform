-- Verify churn_prediction:34_llm_api_key on pg

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'churn'
          AND table_name   = 'project_llm_config'
          AND column_name  = 'openai_api_key'
    ) THEN
        RAISE EXCEPTION 'Coluna openai_api_key não encontrada em churn.project_llm_config.';
    END IF;
END $$;
