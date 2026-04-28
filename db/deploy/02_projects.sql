-- Deploy churn_prediction:02_projects to pg

BEGIN;

CREATE TABLE churn.projects (
    id         SERIAL PRIMARY KEY,
    tenant_id  INTEGER      NOT NULL REFERENCES churn.tenants(id),
    name       VARCHAR(100) NOT NULL,
    slug       VARCHAR(50)  NOT NULL,
    created_at TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (tenant_id, slug)
);

COMMENT ON COLUMN churn.projects.id         IS 'Identificador único do projeto.';
COMMENT ON COLUMN churn.projects.tenant_id  IS 'Tenant ao qual o projeto pertence.';
COMMENT ON COLUMN churn.projects.name       IS 'Nome descritivo do projeto. Ex: "Churn Telecom Brasil".';
COMMENT ON COLUMN churn.projects.slug       IS 'Identificador amigável único dentro do tenant. Ex: "churn-telecom-br".';
COMMENT ON COLUMN churn.projects.created_at IS 'Data e hora de criação do projeto.';

COMMIT;
