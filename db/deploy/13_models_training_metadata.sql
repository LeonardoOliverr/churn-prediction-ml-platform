-- Deploy churn_prediction:13_models_training_metadata to pg
-- requires: 12_champion_challenger

BEGIN;

ALTER TABLE churn.models
    ADD COLUMN hyperparameters JSONB,
    ADD COLUMN training_params JSONB;

COMMENT ON COLUMN churn.models.hyperparameters IS
    'Hiperparametros finais usados pelo estimador, como n_estimators, max_depth, class_weight e random_state.';

COMMENT ON COLUMN churn.models.training_params IS
    'Parametros do processo de treino, como cv_folds, cv_strategy, holdout_size e primary_metric.';

COMMIT;
