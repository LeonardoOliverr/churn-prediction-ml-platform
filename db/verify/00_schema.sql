-- Verify churn_prediction:00_schema on pg

SELECT 1 FROM information_schema.schemata WHERE schema_name = 'churn';
