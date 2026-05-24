-- Deploy churn_prediction:15_evaluation_runs to pg
-- requires: 14_holdout_evaluation

BEGIN;

-- ---------------------------------------------------------------------------
-- churn.evaluation_runs
-- Representa uma execução de avaliação: tenant + projeto + período.
-- Uma row = um "run" auditável com parâmetros de custo fixados no momento.
-- ---------------------------------------------------------------------------

CREATE TABLE churn.evaluation_runs (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL REFERENCES churn.tenants(id),
    project_id       UUID         NOT NULL REFERENCES churn.projects(id),
    period_start     TIMESTAMPTZ  NOT NULL,
    period_end       TIMESTAMPTZ  NOT NULL,
    evaluation_type  VARCHAR(20)  NOT NULL DEFAULT 'manual'
                         CHECK (evaluation_type IN ('monthly', 'weekly', 'manual', 'backtest')),
    fp_cost          NUMERIC(12,2) NOT NULL,
    fn_cost          NUMERIC(12,2) NOT NULL,
    triggered_by     VARCHAR(20)  NOT NULL DEFAULT 'manual'
                         CHECK (triggered_by IN ('scheduler', 'manual', 'api', 'backtest', 'ci')),
    status           VARCHAR(20)  NOT NULL DEFAULT 'running'
                         CHECK (status IN ('running', 'completed', 'failed')),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    metadata         JSONB,
    -- Garante idempotência: apenas um run por tenant/projeto/período/tipo
    UNIQUE (tenant_id, project_id, period_start, period_end, evaluation_type)
);

CREATE INDEX idx_evaluation_runs_tenant_project
    ON churn.evaluation_runs (tenant_id, project_id);

CREATE INDEX idx_evaluation_runs_period
    ON churn.evaluation_runs (period_start, period_end);

CREATE INDEX idx_evaluation_runs_status
    ON churn.evaluation_runs (status)
    WHERE status <> 'completed';

COMMENT ON TABLE churn.evaluation_runs IS
    'Execuções de avaliação de modelos. Cada registro representa um run auditável com período absoluto e parâmetros de custo fixados no momento da execução.';

COMMENT ON COLUMN churn.evaluation_runs.id IS
    'Identificador único do run de avaliação (UUID v4).';
COMMENT ON COLUMN churn.evaluation_runs.tenant_id IS
    'Tenant ao qual o run pertence.';
COMMENT ON COLUMN churn.evaluation_runs.project_id IS
    'Projeto ao qual o run pertence.';
COMMENT ON COLUMN churn.evaluation_runs.period_start IS
    'Início absoluto do período avaliado (UTC), truncado para 00:00:00 do dia. Imutável após criação.';
COMMENT ON COLUMN churn.evaluation_runs.period_end IS
    'Fim absoluto do período avaliado (UTC), truncado para 23:59:59 do dia. Imutável após criação.';
COMMENT ON COLUMN churn.evaluation_runs.evaluation_type IS
    'Tipo da avaliação: monthly (mensal), weekly (semanal), manual (sob demanda), backtest (retrospectivo).';
COMMENT ON COLUMN churn.evaluation_runs.fp_cost IS
    'Custo unitário de falso positivo fixado neste run. Snapshot imutável — não reflete alterações futuras nos parâmetros de negócio.';
COMMENT ON COLUMN churn.evaluation_runs.fn_cost IS
    'Custo unitário de falso negativo fixado neste run. Snapshot imutável — não reflete alterações futuras nos parâmetros de negócio.';
COMMENT ON COLUMN churn.evaluation_runs.triggered_by IS
    'Origem da execução: scheduler (agendado), manual (linha de comando), api (chamada externa), backtest (retroativo), ci (pipeline de CI).';
COMMENT ON COLUMN churn.evaluation_runs.status IS
    'Estado atual do run: running (em andamento), completed (concluído com sucesso), failed (encerrado com erro).';
COMMENT ON COLUMN churn.evaluation_runs.created_at IS
    'Data e hora de criação do run (início da execução).';
COMMENT ON COLUMN churn.evaluation_runs.completed_at IS
    'Data e hora de conclusão do run. NULL enquanto status for running.';
COMMENT ON COLUMN churn.evaluation_runs.metadata IS
    'Metadados livres em JSON: versão do script, flags utilizados, contexto adicional de auditoria.';

-- ---------------------------------------------------------------------------
-- churn.evaluation_run_results
-- Resultado de um modelo específico dentro de um run.
-- Snapshot completo: nome, versão, papel e threshold fixados no momento.
-- ---------------------------------------------------------------------------

CREATE TABLE churn.evaluation_run_results (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_run_id       UUID         NOT NULL REFERENCES churn.evaluation_runs(id),
    tenant_id               UUID         NOT NULL REFERENCES churn.tenants(id),
    project_id              UUID         NOT NULL REFERENCES churn.projects(id),
    model_id                UUID         NOT NULL REFERENCES churn.models(id),
    -- Snapshot do estado operacional no momento do run
    model_name_snapshot     VARCHAR(100) NOT NULL,
    model_version_snapshot  VARCHAR(20)  NOT NULL,
    model_role_snapshot     VARCHAR(20)  NOT NULL DEFAULT 'champion'
                                CHECK (model_role_snapshot IN ('champion', 'challenger', 'shadow', 'unknown')),
    traffic_split_snapshot  NUMERIC(5,4),
    threshold_used          NUMERIC(6,4) NOT NULL,
    -- Matriz de confusão
    tp                      INTEGER      NOT NULL DEFAULT 0,
    fp                      INTEGER      NOT NULL DEFAULT 0,
    fn                      INTEGER      NOT NULL DEFAULT 0,
    tn                      INTEGER      NOT NULL DEFAULT 0,
    -- Métricas derivadas
    precision_score         NUMERIC(6,4),
    recall_score            NUMERIC(6,4),
    f1_score                NUMERIC(6,4),
    roc_auc                 NUMERIC(6,4),
    -- Custo
    fp_cost                 NUMERIC(12,2) NOT NULL,
    fn_cost                 NUMERIC(12,2) NOT NULL,
    total_cost              NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- Volume
    evaluated_predictions   INTEGER      NOT NULL DEFAULT 0,
    missing_actual_labels   INTEGER      NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    metadata                JSONB,
    -- Um modelo avaliado apenas uma vez por run e threshold
    UNIQUE (evaluation_run_id, model_id, threshold_used)
);

CREATE INDEX idx_eval_run_results_run
    ON churn.evaluation_run_results (evaluation_run_id);

CREATE INDEX idx_eval_run_results_model
    ON churn.evaluation_run_results (model_id);

CREATE INDEX idx_eval_run_results_project
    ON churn.evaluation_run_results (project_id);

CREATE INDEX idx_eval_run_results_f1
    ON churn.evaluation_run_results (f1_score DESC NULLS LAST);

COMMENT ON TABLE churn.evaluation_run_results IS
    'Resultado de um modelo específico dentro de um run de avaliação. Preserva snapshot completo do estado operacional (nome, versão, papel, threshold) no momento da execução.';

COMMENT ON COLUMN churn.evaluation_run_results.id IS
    'Identificador único do resultado (UUID v4).';
COMMENT ON COLUMN churn.evaluation_run_results.evaluation_run_id IS
    'Run ao qual este resultado pertence. FK para churn.evaluation_runs.';
COMMENT ON COLUMN churn.evaluation_run_results.tenant_id IS
    'Tenant ao qual o resultado pertence.';
COMMENT ON COLUMN churn.evaluation_run_results.project_id IS
    'Projeto ao qual o resultado pertence.';
COMMENT ON COLUMN churn.evaluation_run_results.model_id IS
    'Modelo avaliado. FK para churn.models — mantido mesmo após arquivamento do modelo.';
COMMENT ON COLUMN churn.evaluation_run_results.model_name_snapshot IS
    'Nome do modelo fixado no momento do run. Preservado mesmo após renomeação ou arquivamento do modelo.';
COMMENT ON COLUMN churn.evaluation_run_results.model_version_snapshot IS
    'Versão do modelo fixada no momento do run. Preservada mesmo após novas versões serem publicadas.';
COMMENT ON COLUMN churn.evaluation_run_results.model_role_snapshot IS
    'Papel operacional do modelo no momento do run: champion (modelo principal), challenger (candidato em teste), shadow (observação sem afetar tráfego) ou unknown (configuração não encontrada).';
COMMENT ON COLUMN churn.evaluation_run_results.traffic_split_snapshot IS
    'Fração do tráfego roteada para este modelo no momento do run. NULL para champion; entre 0 e 1 para challenger.';
COMMENT ON COLUMN churn.evaluation_run_results.threshold_used IS
    'Threshold de decisão aplicado pelo modelo neste run. Probabilidades acima deste valor foram classificadas como churn.';
COMMENT ON COLUMN churn.evaluation_run_results.tp IS
    'Verdadeiros positivos: clientes previstos como churn que efetivamente cancelaram.';
COMMENT ON COLUMN churn.evaluation_run_results.fp IS
    'Falsos positivos: clientes previstos como churn que não cancelaram (custo de ação de retenção desnecessária).';
COMMENT ON COLUMN churn.evaluation_run_results.fn IS
    'Falsos negativos: clientes que cancelaram mas não foram identificados pelo modelo (custo de perda do cliente).';
COMMENT ON COLUMN churn.evaluation_run_results.tn IS
    'Verdadeiros negativos: clientes previstos como não-churn que realmente não cancelaram.';
COMMENT ON COLUMN churn.evaluation_run_results.precision_score IS
    'Precisão do modelo no período: TP / (TP + FP). Proporção de alertas de churn que eram corretos.';
COMMENT ON COLUMN churn.evaluation_run_results.recall_score IS
    'Recall do modelo no período: TP / (TP + FN). Proporção de churns reais que foram identificados.';
COMMENT ON COLUMN churn.evaluation_run_results.f1_score IS
    'F1-score do modelo no período: média harmônica entre precision e recall. Principal métrica de comparação entre modelos.';
COMMENT ON COLUMN churn.evaluation_run_results.roc_auc IS
    'Área sob a curva ROC no período. NULL quando probabilidades individuais não estão disponíveis — requer extensão futura.';
COMMENT ON COLUMN churn.evaluation_run_results.fp_cost IS
    'Custo unitário de falso positivo copiado do run. Torna o resultado self-contained para queries sem join.';
COMMENT ON COLUMN churn.evaluation_run_results.fn_cost IS
    'Custo unitário de falso negativo copiado do run. Torna o resultado self-contained para queries sem join.';
COMMENT ON COLUMN churn.evaluation_run_results.total_cost IS
    'Custo financeiro total estimado: (FP × fp_cost) + (FN × fn_cost).';
COMMENT ON COLUMN churn.evaluation_run_results.evaluated_predictions IS
    'Total de predições do modelo no período que possuem outcome registrado (ground truth disponível).';
COMMENT ON COLUMN churn.evaluation_run_results.missing_actual_labels IS
    'Predições do modelo no período sem outcome registrado. Indica cobertura incompleta do ground truth.';
COMMENT ON COLUMN churn.evaluation_run_results.created_at IS
    'Data e hora de inserção do resultado.';
COMMENT ON COLUMN churn.evaluation_run_results.metadata IS
    'Metadados livres em JSON para extensibilidade futura.';

COMMIT;
