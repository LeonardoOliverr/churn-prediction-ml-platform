-- Deploy churn_prediction:28_model_audit_log to pg
-- requires: 27_model_governance

BEGIN;

CREATE TABLE churn.model_audit_log (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id         UUID         NOT NULL REFERENCES churn.models(id),
    tenant_id        UUID         NOT NULL REFERENCES churn.tenants(id),
    project_id       UUID         NOT NULL REFERENCES churn.projects(id),

    action           VARCHAR(30)  NOT NULL
                     CHECK (action IN (
                         'registered',
                         'approved',
                         'configured',
                         'promoted',
                         'deprecated',
                         'rejected'
                     )),

    old_status       VARCHAR(10),
    new_status       VARCHAR(10),

    changed_by       TEXT         NOT NULL,
    reason           TEXT,
    metrics_snapshot JSONB,

    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_model_audit_log_model_id   ON churn.model_audit_log (model_id);
CREATE INDEX idx_model_audit_log_tenant_id  ON churn.model_audit_log (tenant_id);
CREATE INDEX idx_model_audit_log_created_at ON churn.model_audit_log (created_at DESC);

COMMENT ON TABLE churn.model_audit_log IS
    'Audit trail append-only de todas as transições de status de modelos. '
    'Nunca atualizar ou deletar registros — apenas INSERT.';

COMMENT ON COLUMN churn.model_audit_log.action           IS 'Tipo de evento: registered, approved, configured, promoted, deprecated, rejected.';
COMMENT ON COLUMN churn.model_audit_log.changed_by       IS 'JWT sub de quem executou a ação, ou ''system'' para operações automáticas.';
COMMENT ON COLUMN churn.model_audit_log.metrics_snapshot IS 'Snapshot de F1/recall/custo no momento da ação para contexto histórico.';

COMMIT;
