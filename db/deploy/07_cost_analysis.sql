-- Deploy churn_prediction:07_cost_analysis to pg

BEGIN;

CREATE TABLE churn.cost_analysis (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       NOT NULL REFERENCES churn.tenants(id),
    project_id          INTEGER       NOT NULL REFERENCES churn.projects(id),
    model_id            INTEGER       NOT NULL REFERENCES churn.models(id),
    false_positive_cost NUMERIC(10,2) NOT NULL,
    false_negative_cost NUMERIC(10,2) NOT NULL,
    total_cost          NUMERIC(12,2) NOT NULL,
    threshold_used      NUMERIC(4,3)  NOT NULL,
    evaluated_at        TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON COLUMN churn.cost_analysis.id                  IS 'Identificador único da análise de custo.';
COMMENT ON COLUMN churn.cost_analysis.tenant_id           IS 'Tenant ao qual a análise pertence.';
COMMENT ON COLUMN churn.cost_analysis.project_id          IS 'Projeto ao qual a análise pertence. Cada projeto pode ter custos de FP/FN diferentes.';
COMMENT ON COLUMN churn.cost_analysis.model_id            IS 'Modelo avaliado nesta análise de custo.';
COMMENT ON COLUMN churn.cost_analysis.false_positive_cost IS 'Custo unitário de um falso positivo: cliente classificado como churn que não iria cancelar (custo de ação desnecessária).';
COMMENT ON COLUMN churn.cost_analysis.false_negative_cost IS 'Custo unitário de um falso negativo: cliente que cancelou mas não foi identificado (custo de perda do cliente).';
COMMENT ON COLUMN churn.cost_analysis.total_cost          IS 'Custo total calculado para o conjunto avaliado com o threshold aplicado.';
COMMENT ON COLUMN churn.cost_analysis.threshold_used      IS 'Threshold utilizado na avaliação. Permite comparar o impacto de diferentes thresholds no custo total.';
COMMENT ON COLUMN churn.cost_analysis.evaluated_at        IS 'Data e hora em que a análise de custo foi executada.';

COMMIT;
