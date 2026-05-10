-- Verify churn_prediction:19_grafana_readonly on pg

SELECT 1 FROM pg_roles WHERE rolname = 'grafana_readonly';
SELECT 1 FROM pg_roles WHERE rolname = 'grafana_user';
