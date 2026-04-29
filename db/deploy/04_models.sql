-- Deploy churn_prediction:04_models to pg

BEGIN;

CREATE TABLE churn.models (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(50)  NOT NULL,
    version         VARCHAR(50)  NOT NULL,
    scope           VARCHAR(10)  NOT NULL DEFAULT 'global'
                        CHECK (scope IN ('global', 'tenant', 'project')),
    tenant_id       UUID         REFERENCES churn.tenants(id),
    project_id      UUID         REFERENCES churn.projects(id),
    mlflow_run_id   VARCHAR(100),
    accuracy        NUMERIC(6,4),
    f1_score        NUMERIC(6,4),
    roc_auc         NUMERIC(6,4),
    precision_score NUMERIC(6,4),
    recall_score    NUMERIC(6,4),
    trained_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (name, version)
);

COMMENT ON COLUMN churn.models.id              IS 'Identificador único do modelo (UUID v4).';
COMMENT ON COLUMN churn.models.name            IS 'Nome do algoritmo/modelo. Ex: "MLP", "LogisticRegression", "XGBoost".';
COMMENT ON COLUMN churn.models.version         IS 'Versão do modelo. Ex: "v1", "v2.1".';
COMMENT ON COLUMN churn.models.scope           IS 'Escopo do modelo: global (treinado no dataset completo), tenant (fine-tune por empresa) ou project (fine-tune por projeto).';
COMMENT ON COLUMN churn.models.tenant_id       IS 'Tenant dono do modelo quando scope = tenant ou project. Nulo se global.';
COMMENT ON COLUMN churn.models.project_id      IS 'Projeto dono do modelo quando scope = project. Nulo se global ou tenant.';
COMMENT ON COLUMN churn.models.mlflow_run_id   IS 'ID do run no MLflow que gerou este modelo. Permite rastrear experimentos, métricas e artefatos.';
COMMENT ON COLUMN churn.models.accuracy        IS 'Acurácia do modelo no conjunto de teste.';
COMMENT ON COLUMN churn.models.f1_score        IS 'F1-Score do modelo no conjunto de teste.';
COMMENT ON COLUMN churn.models.roc_auc         IS 'Área sob a curva ROC (AUC) do modelo no conjunto de teste.';
COMMENT ON COLUMN churn.models.precision_score IS 'Precisão do modelo no conjunto de teste.';
COMMENT ON COLUMN churn.models.recall_score    IS 'Recall (sensibilidade) do modelo no conjunto de teste.';
COMMENT ON COLUMN churn.models.trained_at      IS 'Data e hora em que o modelo foi treinado.';

COMMIT;
