-- Deploy churn_prediction:10_api_keys to pg
-- requires: 01_tenants
-- requires: 02_projects

BEGIN;

CREATE TABLE churn.api_keys (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID         NOT NULL REFERENCES churn.tenants(id)  ON DELETE CASCADE,
    project_id   UUID                  REFERENCES churn.projects(id) ON DELETE SET NULL,
    key_hash     TEXT         NOT NULL,
    key_prefix   VARCHAR(20)  NOT NULL,
    scopes       TEXT[]       NOT NULL DEFAULT '{}',
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    expires_at   TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_prefix    ON churn.api_keys (key_prefix) WHERE is_active = TRUE;
CREATE INDEX idx_api_keys_tenant_id ON churn.api_keys (tenant_id);

COMMENT ON TABLE  churn.api_keys              IS 'API keys para autenticação de chamadas de inferência. O segredo nunca é armazenado; apenas o hash bcrypt e os primeiros 20 caracteres (prefix) são persistidos.';
COMMENT ON COLUMN churn.api_keys.id           IS 'Identificador único da API key (UUID v4).';
COMMENT ON COLUMN churn.api_keys.tenant_id    IS 'Tenant dono da key. Cascade delete remove todas as keys ao excluir o tenant.';
COMMENT ON COLUMN churn.api_keys.project_id   IS 'Projeto associado à key. Opcional — NULL indica acesso a todos os projetos do tenant.';
COMMENT ON COLUMN churn.api_keys.key_hash     IS 'Hash bcrypt do segredo completo. Nunca armazene o valor em texto plano.';
COMMENT ON COLUMN churn.api_keys.key_prefix   IS 'Primeiros 20 caracteres da key em texto plano. Usado para lookup eficiente antes da verificação bcrypt.';
COMMENT ON COLUMN churn.api_keys.scopes       IS 'Lista de escopos concedidos. Ex: {predict, predict:batch, admin}.';
COMMENT ON COLUMN churn.api_keys.is_active    IS 'FALSE revoga a key sem excluir o registro (preserva auditoria).';
COMMENT ON COLUMN churn.api_keys.expires_at   IS 'Data/hora de expiração. NULL = sem expiração.';
COMMENT ON COLUMN churn.api_keys.last_used_at IS 'Última vez que a key foi autenticada com sucesso.';
COMMENT ON COLUMN churn.api_keys.created_at   IS 'Data/hora de criação da key.';

COMMIT;
