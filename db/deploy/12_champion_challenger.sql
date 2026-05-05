-- Deploy churn_prediction:12_champion_challenger to pg
-- requires: 11_models_status_and_project_config_semantics

BEGIN;

ALTER TABLE churn.project_model_config
    ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'champion',
    ADD COLUMN traffic_split NUMERIC(4,3) NOT NULL DEFAULT 0.000;

ALTER TABLE churn.project_model_config
    ALTER COLUMN project_id DROP NOT NULL;

ALTER TABLE churn.project_model_config
    ADD CONSTRAINT project_model_config_role_check
        CHECK (role IN ('champion', 'challenger')),
    ADD CONSTRAINT project_model_config_traffic_split_range_check
        CHECK (traffic_split >= 0 AND traffic_split <= 1);

ALTER TABLE churn.project_model_config
    DROP CONSTRAINT IF EXISTS project_model_config_project_id_model_id_key;

DROP INDEX IF EXISTS churn.uq_project_model_config_active;

CREATE UNIQUE INDEX uq_project_model_config_scope_model
    ON churn.project_model_config (tenant_id, project_id, model_id, environment) NULLS NOT DISTINCT;

CREATE UNIQUE INDEX uq_project_model_config_active_champion
    ON churn.project_model_config (tenant_id, project_id, environment) NULLS NOT DISTINCT
    WHERE is_active = TRUE AND role = 'champion';

CREATE UNIQUE INDEX uq_project_model_config_active_challenger
    ON churn.project_model_config (tenant_id, project_id, environment) NULLS NOT DISTINCT
    WHERE is_active = TRUE AND role = 'challenger';

COMMENT ON COLUMN churn.project_model_config.role IS
    'Papel operacional do modelo no escopo tenant/project: champion (modelo principal) ou challenger (candidato em teste).';

COMMENT ON COLUMN churn.project_model_config.traffic_split IS
    'Fracao do trafego roteada para o challenger. Ex: 0.200 = 20%. Para champion, o valor operacional deve ser 0.';

COMMENT ON COLUMN churn.project_model_config.project_id IS
    'Projeto da configuracao operacional. NULL indica escopo de tenant; valor preenchido indica escopo tenant + project.';

COMMENT ON COLUMN churn.project_model_config.is_active IS
    'Indica se esta configuracao esta ativa no escopo tenant/project. Um champion e no maximo um challenger ativos sao permitidos por tenant_id + project_id + environment.';

COMMIT;
