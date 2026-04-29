-- Seed: tenant e projeto padrão para o dataset IBM Telco Churn
-- Executar após `sqitch deploy`, antes de pipeline/load_ibm_telco.py

BEGIN;

INSERT INTO churn.tenants (name, slug)
VALUES ('IBM Telco Demo', 'ibm-telco')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO churn.projects (tenant_id, name, slug)
VALUES (
    (SELECT id FROM churn.tenants WHERE slug = 'ibm-telco'),
    'IBM Telco Churn 2018',
    'telco-churn-2018'
)
ON CONFLICT (tenant_id, slug) DO NOTHING;

COMMIT;
