-- Deploy churn_prediction:03_customers to pg

BEGIN;

CREATE TABLE churn.customers (
    id                SERIAL        PRIMARY KEY,
    tenant_id         INTEGER       NOT NULL REFERENCES churn.tenants(id),
    project_id        INTEGER       NOT NULL REFERENCES churn.projects(id),

    -- Identificação
    customer_id       VARCHAR(20)   NOT NULL,
    customer_count    SMALLINT      DEFAULT 1,

    -- Localização
    country           VARCHAR(50),
    state             VARCHAR(50),
    city              VARCHAR(100),
    zip_code          VARCHAR(10),
    lat_long          VARCHAR(50),
    latitude          NUMERIC(10,6),
    longitude         NUMERIC(10,6),

    -- Perfil
    gender            VARCHAR(10),
    senior_citizen    BOOLEAN,
    partner           BOOLEAN,
    dependents        BOOLEAN,

    -- Serviços
    tenure_months     INTEGER,
    phone_service     BOOLEAN,
    multiple_lines    VARCHAR(20),
    internet_service  VARCHAR(20),
    online_security   VARCHAR(20),
    online_backup     VARCHAR(20),
    device_protection VARCHAR(20),
    tech_support      VARCHAR(20),
    streaming_tv      VARCHAR(20),
    streaming_movies  VARCHAR(20),

    -- Contrato e pagamento
    contract          VARCHAR(20),
    paperless_billing BOOLEAN,
    payment_method    VARCHAR(30),
    monthly_charges   NUMERIC(8,2),
    total_charges     NUMERIC(10,2),

    -- Churn (target)
    churn_label       VARCHAR(3),
    churn_value       SMALLINT      CHECK (churn_value IN (0, 1)),
    churn_score       SMALLINT      CHECK (churn_score BETWEEN 0 AND 100),
    cltv              INTEGER,
    churn_reason      TEXT,

    -- Metadados
    is_synthetic      BOOLEAN       DEFAULT FALSE,
    created_at        TIMESTAMPTZ   DEFAULT NOW(),

    UNIQUE (project_id, customer_id)
);

-- Identificação
COMMENT ON COLUMN churn.customers.customer_id      IS 'Identificador único do cliente.';
COMMENT ON COLUMN churn.customers.customer_count   IS 'Valor usado em relatórios e dashboards para somar o número de clientes em um conjunto filtrado.';

-- Localização
COMMENT ON COLUMN churn.customers.country          IS 'País de residência principal do cliente.';
COMMENT ON COLUMN churn.customers.state            IS 'Estado de residência principal do cliente.';
COMMENT ON COLUMN churn.customers.city             IS 'Cidade de residência principal do cliente.';
COMMENT ON COLUMN churn.customers.zip_code         IS 'CEP da residência principal do cliente.';
COMMENT ON COLUMN churn.customers.lat_long         IS 'Latitude e longitude combinadas da residência principal do cliente.';
COMMENT ON COLUMN churn.customers.latitude         IS 'Latitude da residência principal do cliente.';
COMMENT ON COLUMN churn.customers.longitude        IS 'Longitude da residência principal do cliente.';

-- Perfil
COMMENT ON COLUMN churn.customers.gender           IS 'Gênero do cliente: Male (Masculino), Female (Feminino).';
COMMENT ON COLUMN churn.customers.senior_citizen   IS 'Indica se o cliente tem 65 anos ou mais.';
COMMENT ON COLUMN churn.customers.partner          IS 'Indica se o cliente possui parceiro(a).';
COMMENT ON COLUMN churn.customers.dependents       IS 'Indica se o cliente mora com dependentes (filhos, pais, avós, etc.).';

-- Serviços
COMMENT ON COLUMN churn.customers.tenure_months    IS 'Total de meses que o cliente está com a empresa até o final do trimestre.';
COMMENT ON COLUMN churn.customers.phone_service    IS 'Indica se o cliente assina serviço de telefone fixo.';
COMMENT ON COLUMN churn.customers.multiple_lines   IS 'Indica se o cliente assina múltiplas linhas telefônicas.';
COMMENT ON COLUMN churn.customers.internet_service IS 'Indica se o cliente assina serviço de internet: Não, DSL, Fibra Óptica, Cable.';
COMMENT ON COLUMN churn.customers.online_security  IS 'Indica se o cliente assina serviço adicional de segurança online.';
COMMENT ON COLUMN churn.customers.online_backup    IS 'Indica se o cliente assina serviço adicional de backup online.';
COMMENT ON COLUMN churn.customers.device_protection IS 'Indica se o cliente assina plano adicional de proteção de dispositivos.';
COMMENT ON COLUMN churn.customers.tech_support     IS 'Indica se o cliente assina plano adicional de suporte técnico com tempo de espera reduzido.';
COMMENT ON COLUMN churn.customers.streaming_tv     IS 'Indica se o cliente usa a internet para streaming de TV via provedores terceiros.';
COMMENT ON COLUMN churn.customers.streaming_movies IS 'Indica se o cliente usa a internet para streaming de filmes via provedores terceiros.';

-- Contrato e pagamento
COMMENT ON COLUMN churn.customers.contract         IS 'Tipo de contrato atual do cliente: Mensal, Um Ano, Dois Anos.';
COMMENT ON COLUMN churn.customers.paperless_billing IS 'Indica se o cliente optou por fatura digital (sem papel).';
COMMENT ON COLUMN churn.customers.payment_method   IS 'Forma de pagamento do cliente: Débito bancário, Cartão de crédito, Cheque enviado pelo correio.';
COMMENT ON COLUMN churn.customers.monthly_charges  IS 'Valor total mensal cobrado ao cliente por todos os seus serviços.';
COMMENT ON COLUMN churn.customers.total_charges    IS 'Total cobrado ao cliente até o final do trimestre.';

-- Churn
COMMENT ON COLUMN churn.customers.churn_label      IS 'Yes = cliente cancelou no trimestre. No = cliente permaneceu. Relacionado diretamente a churn_value.';
COMMENT ON COLUMN churn.customers.churn_value      IS '1 = cliente cancelou no trimestre. 0 = cliente permaneceu. Relacionado diretamente a churn_label.';
COMMENT ON COLUMN churn.customers.churn_score      IS 'Pontuação de 0 a 100 calculada pelo IBM SPSS Modeler. Quanto maior, maior a probabilidade de churn.';
COMMENT ON COLUMN churn.customers.cltv             IS 'Customer Lifetime Value (Valor do Ciclo de Vida do Cliente). Clientes de alto valor devem ser monitorados para risco de churn.';
COMMENT ON COLUMN churn.customers.churn_reason     IS 'Motivo específico pelo qual o cliente cancelou. Relacionado à categoria de churn.';

-- Metadados
COMMENT ON COLUMN churn.customers.is_synthetic     IS 'Flag indicando se o registro foi gerado sinteticamente (não veio do dataset IBM original).';

COMMIT;
