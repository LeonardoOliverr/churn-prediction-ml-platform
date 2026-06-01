-- Deploy churn_prediction:34_llm_api_key to pg
-- requires: 33_predictions_explanation_text

BEGIN;

ALTER TABLE churn.project_llm_config
    ADD COLUMN openai_api_key BYTEA;

COMMENT ON COLUMN churn.project_llm_config.openai_api_key IS
    'Chave OpenAI criptografada com pgp_sym_encrypt (pgcrypto). '
    'NULL = usa variável de ambiente OPENAI_API_KEY do container (fallback global).';

COMMIT;
