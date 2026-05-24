-- Revert churn_prediction:13_models_training_metadata from pg

BEGIN;

ALTER TABLE churn.models
    DROP COLUMN IF EXISTS training_params,
    DROP COLUMN IF EXISTS hyperparameters;

COMMIT;
