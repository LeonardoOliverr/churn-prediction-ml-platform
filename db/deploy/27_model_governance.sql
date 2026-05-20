-- Deploy churn_prediction:27_model_governance to pg
-- requires: 26_predictions_batch_id

BEGIN;

ALTER TABLE churn.models
    -- Aprovação formal
    ADD COLUMN approved_by         TEXT,
    ADD COLUMN approved_at         TIMESTAMPTZ,

    -- Ciclo de vida
    ADD COLUMN deprecated_at       TIMESTAMPTZ,
    ADD COLUMN deprecation_reason  TEXT,
    ADD COLUMN successor_model_id  UUID REFERENCES churn.models(id),

    -- Dataset snapshot
    ADD COLUMN training_row_count  INTEGER,
    ADD COLUMN training_churn_rate NUMERIC(6,4),
    ADD COLUMN training_period     TSTZRANGE,

    -- Tags e classificação livre
    ADD COLUMN tags                TEXT[]  DEFAULT '{}',
    ADD COLUMN notes               TEXT;

CREATE INDEX idx_models_tags ON churn.models USING GIN (tags);

COMMENT ON COLUMN churn.models.approved_by         IS 'JWT sub de quem aprovou o modelo para produção.';
COMMENT ON COLUMN churn.models.approved_at         IS 'Timestamp da aprovação formal para produção.';
COMMENT ON COLUMN churn.models.deprecated_at       IS 'Timestamp em que o modelo foi depreciado.';
COMMENT ON COLUMN churn.models.deprecation_reason  IS 'Motivo da depreciação (ex: superado por xgboost v4).';
COMMENT ON COLUMN churn.models.successor_model_id  IS 'UUID do modelo que substituiu este. Permite reconstruir cadeia v1→v2→v4.';
COMMENT ON COLUMN churn.models.training_row_count  IS 'Número de linhas usadas no treino. Detecta modelos treinados em datasets diferentes.';
COMMENT ON COLUMN churn.models.training_churn_rate IS 'Taxa de churn no dataset de treino.';
COMMENT ON COLUMN churn.models.training_period     IS 'Janela temporal dos dados de treino (TSTZRANGE).';
COMMENT ON COLUMN churn.models.tags                IS 'Tags livres para filtro rápido (ex: overfitting, challenger, v2-tuning).';
COMMENT ON COLUMN churn.models.notes               IS 'Observações livres do Data Scientist sobre o modelo.';

COMMIT;
