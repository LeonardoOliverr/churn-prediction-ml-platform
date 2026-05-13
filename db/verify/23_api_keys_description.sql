-- Verify churn_prediction:23_api_keys_description on pg

SELECT description FROM churn.api_keys LIMIT 1;
