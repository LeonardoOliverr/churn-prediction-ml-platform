-- Deploy churn_prediction:33_predictions_explanation_text to pg
-- requires: 32_project_llm_config

BEGIN;

-- Colunas de saída LLM em churn.predictions
ALTER TABLE churn.predictions
    ADD COLUMN explanation_text    TEXT,
    ADD COLUMN recommended_actions TEXT;

COMMENT ON COLUMN churn.predictions.explanation_text IS
    'Explicação em linguagem natural gerada por LLM a partir dos valores SHAP.
     Null enquanto o job de tradução não processar a predição, ou quando LLM está desabilitado
     para o projeto (project_llm_config.enabled = FALSE).';

COMMENT ON COLUMN churn.predictions.recommended_actions IS
    'Ações de retenção recomendadas pelo LLM com base nos fatores de risco SHAP.
     Null nas mesmas condições que explanation_text.';

-- Log de auditoria e custo de chamadas LLM
CREATE TABLE churn.llm_usage_log (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID        NOT NULL REFERENCES churn.tenants(id),
    project_id        UUID        NOT NULL REFERENCES churn.projects(id),
    prediction_id     UUID        NOT NULL REFERENCES churn.predictions(id),
    model_id          TEXT        NOT NULL,
    prompt_tokens     INT         NOT NULL,
    completion_tokens INT         NOT NULL,
    cost_usd          NUMERIC(10,6),
    generated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX llm_usage_log_project_generated
    ON churn.llm_usage_log (project_id, generated_at DESC);

CREATE INDEX llm_usage_log_prediction
    ON churn.llm_usage_log (prediction_id);

COMMENT ON TABLE churn.llm_usage_log IS
    'Audit trail append-only de chamadas LLM para geração de explanation_text + recommended_actions.
     Registra modelo usado, tokens consumidos e custo calculado no momento da geração.
     Permite rastrear qual modelo gerou cada explicação mesmo após troca de model_id em project_llm_config,
     e agregar custo por modelo/projeto/período para controle operacional.';

COMMENT ON COLUMN churn.llm_usage_log.model_id IS
    'ID do modelo usado no momento da geração (snapshot — independente do project_llm_config atual).';

COMMENT ON COLUMN churn.llm_usage_log.prompt_tokens IS
    'Tokens de entrada (prompt) reportados pela API OpenAI em response.usage.prompt_tokens.';

COMMENT ON COLUMN churn.llm_usage_log.completion_tokens IS
    'Tokens de saída (completion) reportados pela API OpenAI em response.usage.completion_tokens.';

COMMENT ON COLUMN churn.llm_usage_log.cost_usd IS
    'Custo estimado em USD calculado via project_llm_config.cost_per_1m_input/output.
     NULL se o modelo não tiver preço cadastrado na config.';

COMMIT;
