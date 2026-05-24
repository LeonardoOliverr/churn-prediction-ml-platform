-- Revert churn_prediction:02_projects from pg

BEGIN;

DROP TABLE IF EXISTS churn.projects;

COMMIT;
