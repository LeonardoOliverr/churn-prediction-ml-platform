-- Revert churn_prediction:19_grafana_readonly from pg

BEGIN;
DROP USER IF EXISTS grafana_user;
DROP ROLE IF EXISTS grafana_readonly;
COMMIT;
