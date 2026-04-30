-- Deploy churn_prediction:09_models_status to pg
-- requires: 04_models

BEGIN;

ALTER TABLE churn.models
    ADD COLUMN status VARCHAR(10) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'shadow', 'archived'));

COMMENT ON COLUMN churn.models.status IS
    'Estado operacional do modelo: active (em produção), shadow (paralelo sem impacto no usuário), archived (histórico).';

COMMIT;
