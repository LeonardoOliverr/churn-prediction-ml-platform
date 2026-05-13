-- Deploy churn_prediction:23_api_keys_description to pg
-- requires: 22_model_performance_result_costs
--
-- Adiciona coluna description opcional em api_keys para identificação humana da key.

BEGIN;

SET LOCAL client_min_messages = WARNING;
ALTER TABLE churn.api_keys ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON COLUMN churn.api_keys.description IS 'Descrição opcional da key para identificação humana (ex: "Integração CRM").';

COMMIT;
