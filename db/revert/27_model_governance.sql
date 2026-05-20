-- Revert churn_prediction:27_model_governance from pg

BEGIN;

DROP INDEX IF EXISTS churn.idx_models_tags;

ALTER TABLE churn.models
    DROP COLUMN IF EXISTS approved_by,
    DROP COLUMN IF EXISTS approved_at,
    DROP COLUMN IF EXISTS deprecated_at,
    DROP COLUMN IF EXISTS deprecation_reason,
    DROP COLUMN IF EXISTS successor_model_id,
    DROP COLUMN IF EXISTS training_row_count,
    DROP COLUMN IF EXISTS training_churn_rate,
    DROP COLUMN IF EXISTS training_period,
    DROP COLUMN IF EXISTS tags,
    DROP COLUMN IF EXISTS notes;

COMMIT;
