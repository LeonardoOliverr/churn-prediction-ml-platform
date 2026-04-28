-- Deploy churn_prediction:05_project_model_config to pg

BEGIN;

CREATE TABLE churn.project_model_config (
    id            SERIAL PRIMARY KEY,
    tenant_id     INTEGER      NOT NULL REFERENCES churn.tenants(id),
    project_id    INTEGER      NOT NULL REFERENCES churn.projects(id),
    model_id      INTEGER      NOT NULL REFERENCES churn.models(id),
    threshold     NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    is_active     BOOLEAN      DEFAULT TRUE,
    configured_at TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (project_id, model_id)
);

COMMENT ON COLUMN churn.project_model_config.id            IS 'Identificador único da configuração.';
COMMENT ON COLUMN churn.project_model_config.tenant_id     IS 'Tenant ao qual a configuração pertence.';
COMMENT ON COLUMN churn.project_model_config.project_id    IS 'Projeto ao qual a configuração pertence.';
COMMENT ON COLUMN churn.project_model_config.model_id      IS 'Modelo configurado para este projeto. Pode ser um modelo global com threshold customizado.';
COMMENT ON COLUMN churn.project_model_config.threshold     IS 'Threshold de decisão aplicado pelo projeto. Probabilidades acima deste valor são classificadas como churn. Padrão: 0.500.';
COMMENT ON COLUMN churn.project_model_config.is_active     IS 'Indica se esta configuração está ativa. Apenas uma configuração ativa por projeto deve ser usada na inferência.';
COMMENT ON COLUMN churn.project_model_config.configured_at IS 'Data e hora em que a configuração foi registrada.';

COMMIT;
