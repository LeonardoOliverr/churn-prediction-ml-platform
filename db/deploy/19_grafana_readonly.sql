-- Deploy churn_prediction:19_grafana_readonly to pg
-- requires: 18_analytics_enhancements
--
-- Cria role grafana_readonly com SELECT restrito às tabelas e views do schema churn.
-- Cria usuário grafana_user para o datasource do Grafana, isolado das credenciais da aplicação.

BEGIN;

-- Roles são objetos de cluster (compartilhados entre databases).
-- DO block evita falha quando a role já existe em outro database do mesmo cluster.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grafana_readonly') THEN
    CREATE ROLE grafana_readonly;
  END IF;
END $$;

DO $$ BEGIN
  EXECUTE format(
    'GRANT CONNECT ON DATABASE %I TO grafana_readonly',
    current_database()
  );
END $$;

GRANT USAGE ON SCHEMA churn TO grafana_readonly;

GRANT SELECT ON
    churn.tenants,
    churn.projects,
    churn.predictions,
    churn.api_keys,
    churn.outcomes,
    churn.evaluation_runs,
    churn.evaluation_run_results,
    churn.model_performance,
    churn.evaluation_comparison
TO grafana_readonly;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grafana_user') THEN
    CREATE USER grafana_user WITH PASSWORD 'grafana_pass' IN ROLE grafana_readonly;
  END IF;
END $$;

COMMIT;
