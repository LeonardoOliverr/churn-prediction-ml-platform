-- Deploy churn_prediction:14_holdout_evaluation to pg

BEGIN;

-- Parte A: coluna split em churn.customers
-- Distribui registros existentes via hash MD5 determinístico.
-- Equivalente à função assign_split() em pipeline/load_ibm_telco.py.
ALTER TABLE churn.customers
    ADD COLUMN split VARCHAR(10) NOT NULL DEFAULT 'train'
        CHECK (split IN ('train', 'holdout'));

UPDATE churn.customers SET split = CASE
    WHEN (('x' || md5(customer_id))::bit(32)::bigint + 2147483648)::numeric
         / 4294967296.0 < 0.3
    THEN 'holdout'
    ELSE 'train'
END;

COMMENT ON COLUMN churn.customers.split IS 'Partição determinística do cliente: train (70%) ou holdout (30%). Atribuída via MD5 do customer_id.';

-- Parte B: tabela churn.outcomes
-- Registra o resultado real de churn para predições realizadas sobre clientes holdout.
-- prediction_id → churn.predictions: o que o modelo previu.
-- churned       → o que realmente aconteceu (ground truth).
CREATE TABLE churn.outcomes (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id UUID        NOT NULL REFERENCES churn.predictions(id),
    tenant_id     UUID        NOT NULL REFERENCES churn.tenants(id),
    project_id    UUID        NOT NULL REFERENCES churn.projects(id),
    customer_id   VARCHAR(20) NOT NULL,
    churned       BOOLEAN     NOT NULL,
    confirmed_at  TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (prediction_id)
);

COMMENT ON TABLE  churn.outcomes               IS 'Resultado real de churn para predições realizadas sobre clientes holdout. Fecha o loop entre o que o modelo previu e o que de fato aconteceu.';
COMMENT ON COLUMN churn.outcomes.id            IS 'Identificador único do outcome (UUID v4).';
COMMENT ON COLUMN churn.outcomes.prediction_id IS 'Predição avaliada. Relação 1:1 com churn.predictions — cada predição tem no máximo um outcome.';
COMMENT ON COLUMN churn.outcomes.tenant_id     IS 'Tenant ao qual o outcome pertence.';
COMMENT ON COLUMN churn.outcomes.project_id    IS 'Projeto ao qual o outcome pertence.';
COMMENT ON COLUMN churn.outcomes.customer_id   IS 'Identificador do cliente no sistema de origem.';
COMMENT ON COLUMN churn.outcomes.churned       IS 'Verdade sobre o churn: TRUE se o cliente efetivamente cancelou (churn_value=1 em churn.customers), FALSE caso contrário.';
COMMENT ON COLUMN churn.outcomes.confirmed_at  IS 'Momento em que o churn foi confirmado. Em simulação holdout, equivale a requested_at da predição. Em produção real, representa quando o cancelamento foi efetivamente registrado.';
COMMENT ON COLUMN churn.outcomes.created_at    IS 'Data e hora de inserção do registro.';

CREATE INDEX idx_outcomes_project_id   ON churn.outcomes (project_id);
CREATE INDEX idx_outcomes_confirmed_at ON churn.outcomes (confirmed_at);
CREATE INDEX idx_outcomes_customer_id  ON churn.outcomes (customer_id);

COMMIT;
