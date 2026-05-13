-- Deploy churn_prediction:21_cost_model_config to pg
-- requires: 20_challenger_cost_normalization
--
-- Cria churn.cost_model_config para centralizar a configuração do modelo de custo
-- por tenant/projeto. Substitui custo flat uniforme por custo real derivado de
-- cltv e monthly_charges de cada cliente.

BEGIN;

CREATE TABLE churn.cost_model_config (
    id                        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 UUID         NOT NULL REFERENCES churn.tenants(id),
    project_id                UUID         REFERENCES churn.projects(id),
    -- NULL = aplica a todos os projetos do tenant
    -- NOT NULL = sobrescreve para este projeto específico

    cost_model                VARCHAR(20)  NOT NULL DEFAULT 'flat'
                                  CHECK (cost_model IN ('flat', 'cltv', 'monthly_charges')),

    -- Modo flat (retrocompatível com comportamento atual)
    fp_cost_flat              NUMERIC(12,2),
    fn_cost_flat              NUMERIC(12,2),

    -- Custo do FP (compartilhado entre cltv e monthly_charges):
    --   fp_cost = monthly_charges × fp_cost_months × fp_cost_discount
    fp_cost_months            NUMERIC(5,2)  NOT NULL DEFAULT 2.0,
    fp_cost_discount          NUMERIC(5,4)  NOT NULL DEFAULT 0.20,

    -- Modo cltv: fn_cost = cltv × fn_cost_cltv_multiplier
    fn_cost_cltv_multiplier   NUMERIC(5,4)  NOT NULL DEFAULT 1.0,

    -- Modo monthly_charges: fn_cost = monthly_charges × fn_cost_months_multiplier
    fn_cost_months_multiplier NUMERIC(5,2)  NOT NULL DEFAULT 12.0,

    is_active                 BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    notes                     TEXT,

    UNIQUE (tenant_id, project_id, cost_model)
);

COMMENT ON TABLE churn.cost_model_config IS
    'Configuração do modelo de custo operacional por tenant/projeto. '
    'Resolve em cascata: project-level > tenant-level > fallback flat via CLI. '
    'Modos: flat = custo fixo por FP/FN; cltv = derivado de cltv e monthly_charges do cliente; '
    'monthly_charges = derivado de monthly_charges quando cltv não está disponível.';

COMMENT ON COLUMN churn.cost_model_config.project_id IS
    'NULL = configuração de fallback para todos os projetos do tenant. '
    'NOT NULL = sobrescreve para o projeto específico (maior prioridade).';

COMMENT ON COLUMN churn.cost_model_config.cost_model IS
    'Modo de cálculo: flat usa fp_cost_flat/fn_cost_flat fixos; '
    'cltv usa cltv × fn_cost_cltv_multiplier para FN e monthly_charges × fp_cost_months × fp_cost_discount para FP; '
    'monthly_charges usa monthly_charges × fn_cost_months_multiplier para FN.';

COMMENT ON COLUMN churn.cost_model_config.fp_cost_months IS
    'Meses de mensalidade usados para estimar o custo de retenção desnecessária (FP). '
    'Ex: 2.0 = custo de 2 meses de oferta de retenção.';

COMMENT ON COLUMN churn.cost_model_config.fp_cost_discount IS
    'Percentual de desconto aplicado na mensalidade para o custo de FP. '
    'Ex: 0.20 = 20% de desconto na fatura. FP cost = monthly_charges × fp_cost_months × 0.20.';

COMMENT ON COLUMN churn.cost_model_config.fn_cost_cltv_multiplier IS
    'Fração do CLTV perdida em um FN (churner não detectado). '
    'Ex: 1.0 = 100% do CLTV perdido. FN cost = cltv × 1.0.';

COMMENT ON COLUMN churn.cost_model_config.fn_cost_months_multiplier IS
    'Meses de mensalidade perdidos em um FN no modo monthly_charges. '
    'Ex: 12.0 = 12 meses de receita perdidos. FN cost = monthly_charges × 12.0.';

COMMIT;
