-- Revert churn_prediction:29_rename_model_statuses from pg

BEGIN;

ALTER TABLE churn.models DROP CONSTRAINT models_status_check;

UPDATE churn.models SET status = 'trained'  WHERE status IN ('candidate', 'rejected');
UPDATE churn.models SET status = 'archived' WHERE status = 'retired';

ALTER TABLE churn.models
    ALTER COLUMN status SET DEFAULT 'trained',
    ADD CONSTRAINT models_status_check
        CHECK (status IN ('trained', 'validated', 'approved', 'archived'));

COMMIT;
