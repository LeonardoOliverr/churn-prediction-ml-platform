-- Deploy churn_prediction:26_predictions_batch_id to pg
-- requires: 25_cost_model_config_project_required

BEGIN;

ALTER TABLE churn.predictions
    ADD COLUMN eval_batch_id UUID;

CREATE INDEX idx_predictions_eval_batch_id
    ON churn.predictions (eval_batch_id)
    WHERE eval_batch_id IS NOT NULL;

COMMENT ON COLUMN churn.predictions.eval_batch_id IS
    'UUID do ciclo de avaliação que gerou esta predição. '
    'Permite isolar predições de um batch específico de predict_holdout_batch.py '
    'evitando contaminação entre múltiplos ciclos de avaliação.';

COMMIT;
