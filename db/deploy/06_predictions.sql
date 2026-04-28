-- Deploy churn_prediction:06_predictions to pg

BEGIN;

CREATE TABLE churn.predictions (
    id             SERIAL PRIMARY KEY,
    tenant_id      INTEGER      NOT NULL REFERENCES churn.tenants(id),
    project_id     INTEGER      NOT NULL REFERENCES churn.projects(id),
    customer_id    VARCHAR(20)  NOT NULL,
    model_id       INTEGER      NOT NULL REFERENCES churn.models(id),
    churn_prob     NUMERIC(5,4) NOT NULL,
    churn_pred     BOOLEAN      NOT NULL,
    threshold_used NUMERIC(4,3) NOT NULL,
    latency_ms     INTEGER,
    requested_at   TIMESTAMPTZ  DEFAULT NOW()
);

COMMENT ON COLUMN churn.predictions.id             IS 'Identificador único da predição.';
COMMENT ON COLUMN churn.predictions.tenant_id      IS 'Tenant que originou a requisição de inferência.';
COMMENT ON COLUMN churn.predictions.project_id     IS 'Projeto que originou a requisição de inferência.';
COMMENT ON COLUMN churn.predictions.customer_id    IS 'Identificador do cliente para o qual a predição foi gerada.';
COMMENT ON COLUMN churn.predictions.model_id       IS 'Modelo utilizado para gerar esta predição.';
COMMENT ON COLUMN churn.predictions.churn_prob     IS 'Probabilidade de churn retornada pelo modelo. Valor entre 0.0000 e 1.0000.';
COMMENT ON COLUMN churn.predictions.churn_pred     IS 'Decisão final após aplicação do threshold. True = churn previsto, False = cliente mantido.';
COMMENT ON COLUMN churn.predictions.threshold_used IS 'Threshold aplicado no momento da predição para converter probabilidade em decisão binária.';
COMMENT ON COLUMN churn.predictions.latency_ms     IS 'Tempo de resposta da API em milissegundos. Usado para monitoramento de performance.';
COMMENT ON COLUMN churn.predictions.requested_at   IS 'Data e hora em que a predição foi solicitada.';

COMMIT;
