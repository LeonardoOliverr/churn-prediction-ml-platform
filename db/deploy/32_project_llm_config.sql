-- Deploy churn_prediction:32_project_llm_config to pg
-- requires: 31_predictions_shap

BEGIN;

CREATE TABLE churn.project_llm_config (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES churn.tenants(id),
    project_id          UUID        NOT NULL REFERENCES churn.projects(id),
    model_id            TEXT        NOT NULL DEFAULT 'gpt-4o-mini',
    max_tokens          INT         NOT NULL DEFAULT 300,
    prompt_file         TEXT        NOT NULL DEFAULT 'shap_translation_pt.txt',
    enabled             BOOLEAN     NOT NULL DEFAULT TRUE,
    -- Preço por milhão de tokens (USD) — usado para calcular cost_usd em llm_usage_log
    cost_per_1m_input   NUMERIC(10,6) NOT NULL DEFAULT 0.150000,
    cost_per_1m_output  NUMERIC(10,6) NOT NULL DEFAULT 0.600000,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id)
);

COMMENT ON TABLE churn.project_llm_config IS
    'Configuração do modelo LLM usado para traduzir valores SHAP para linguagem de negócio, por projeto.
     Segue o mesmo padrão de project_model_config e cost_model_config.
     Apenas OPENAI_API_KEY permanece em variável de ambiente — o restante fica nesta tabela.';

COMMENT ON COLUMN churn.project_llm_config.model_id IS
    'ID do modelo OpenAI. Ex: gpt-4o-mini (padrão — rápido e barato para texto curto).';

COMMENT ON COLUMN churn.project_llm_config.max_tokens IS
    'Limite máximo de tokens na resposta do LLM. 300 é suficiente para explicação + ações.';

COMMENT ON COLUMN churn.project_llm_config.prompt_file IS
    'Nome do arquivo .txt em ml/explainability/prompts/ com o template do prompt.
     Permite trocar tom ou idioma por projeto sem alterar código.';

COMMENT ON COLUMN churn.project_llm_config.enabled IS
    'FALSE desliga a tradução LLM para o projeto sem remover a configuração.';

COMMENT ON COLUMN churn.project_llm_config.cost_per_1m_input IS
    'Custo em USD por milhão de tokens de entrada (prompt). Padrão: gpt-4o-mini $0.150/1M.
     Atualizar ao trocar de modelo para manter cálculo de custo correto em llm_usage_log.';

COMMENT ON COLUMN churn.project_llm_config.cost_per_1m_output IS
    'Custo em USD por milhão de tokens de saída (completion). Padrão: gpt-4o-mini $0.600/1M.';

-- Seed para o projeto padrão IBM Telco (gpt-4o-mini pricing)
INSERT INTO churn.project_llm_config (
    tenant_id, project_id, model_id, max_tokens, prompt_file, enabled,
    cost_per_1m_input, cost_per_1m_output
)
SELECT t.id, p.id, 'gpt-4o-mini', 300, 'shap_translation_pt.txt', TRUE,
       0.150000, 0.600000
FROM   churn.tenants  t
JOIN   churn.projects p ON p.tenant_id = t.id
WHERE  t.slug = 'ibm-telco'
  AND  p.slug = 'telco-churn-2018';

COMMIT;
