-- Deploy churn_prediction:00_schema to pg

BEGIN;

CREATE SCHEMA churn;

-- gen_random_uuid() é built-in no PostgreSQL 13+; não requer extensão
-- Habilitamos pgcrypto apenas como fallback para ambientes legados
CREATE EXTENSION IF NOT EXISTS pgcrypto;

COMMIT;
