-- Verify churn_prediction:31_predictions_shap on pg

-- coluna existe e é nullable JSONB
SELECT shap_values FROM churn.predictions LIMIT 1;
