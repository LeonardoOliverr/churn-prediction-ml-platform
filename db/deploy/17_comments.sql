-- Deploy churn_prediction:17_comments to pg
-- requires: 16_deprecate_cost_analysis
--
-- Adiciona COMMENT ON TABLE em todas as tabelas do schema churn que ainda não
-- possuíam comentário, e preenche colunas ausentes em churn.customers.

BEGIN;

-- ---------------------------------------------------------------------------
-- churn.tenants
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.tenants IS
    'Empresas ou clientes que utilizam a plataforma. Unidade raiz de isolamento multi-tenant: todos os dados de negócio estão vinculados a um tenant.';

-- ---------------------------------------------------------------------------
-- churn.projects
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.projects IS
    'Projetos de predição de churn dentro de um tenant. Cada projeto representa um contexto independente de dados, modelos e configurações. Ex: "Churn Telecom Brasil", "Churn B2B 2024".';

-- ---------------------------------------------------------------------------
-- churn.customers
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.customers IS
    'Clientes carregados via pipeline de ingestão. Cada registro representa um cliente do tenant/projeto com suas features de perfil, serviços, contrato e churn real. Base para treinamento e avaliação holdout.';

COMMENT ON COLUMN churn.customers.id         IS 'Identificador único do registro de cliente na plataforma (UUID v4). Diferente do customer_id original do dataset de origem.';
COMMENT ON COLUMN churn.customers.tenant_id  IS 'Tenant ao qual o cliente pertence.';
COMMENT ON COLUMN churn.customers.project_id IS 'Projeto ao qual o cliente pertence.';
COMMENT ON COLUMN churn.customers.created_at IS 'Data e hora de inserção do registro na plataforma.';

-- ---------------------------------------------------------------------------
-- churn.models
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.models IS
    'Catálogo de modelos de machine learning treinados e registrados na plataforma. Cada registro representa uma versão de um algoritmo com suas métricas de treino e metadados do MLflow.';

-- ---------------------------------------------------------------------------
-- churn.project_model_config
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.project_model_config IS
    'Configuração operacional que vincula um modelo a um tenant/projeto. Define qual modelo está ativo em produção, o threshold de decisão e o papel (champion ou challenger). Um champion e no máximo um challenger ativos são permitidos por tenant/projeto/ambiente.';

-- ---------------------------------------------------------------------------
-- churn.predictions
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.predictions IS
    'Log de inferências realizadas pela API. Cada registro representa uma predição de churn para um cliente específico, com a probabilidade retornada, a decisão binária, o threshold aplicado e o modelo utilizado.';

-- ---------------------------------------------------------------------------
-- churn.cost_analysis (deprecated — mantida para histórico)
-- ---------------------------------------------------------------------------

COMMENT ON TABLE churn.cost_analysis IS
    'DEPRECATED desde migration 16. Substituída por churn.evaluation_runs + churn.evaluation_run_results. Mantida para preservação de dados históricos. Não inserir novos registros. Use a view churn.cost_analysis_v2 para queries de compatibilidade.';

COMMIT;
