-- Deploy churn_prediction:01_tenants to pg

BEGIN;

CREATE TABLE churn.tenants (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(100) NOT NULL,
    slug       VARCHAR(50)  NOT NULL UNIQUE,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

COMMENT ON COLUMN churn.tenants.id         IS 'Identificador único do tenant (UUID v4).';
COMMENT ON COLUMN churn.tenants.name       IS 'Nome completo da empresa/cliente da plataforma.';
COMMENT ON COLUMN churn.tenants.slug       IS 'Identificador amigável e único globalmente. Usado em URLs e integrações. Ex: "acme-corp".';
COMMENT ON COLUMN churn.tenants.created_at IS 'Data e hora de cadastro do tenant.';

COMMIT;
