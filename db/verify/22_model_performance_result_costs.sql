-- Verify churn_prediction:22_model_performance_result_costs on pg

SELECT 1 FROM information_schema.views
WHERE table_schema = 'churn' AND table_name = 'model_performance';
