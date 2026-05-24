-- Deploy churn_prediction:31_predictions_shap to pg
-- requires: 30_update_audit_actions

BEGIN;

ALTER TABLE churn.predictions
    ADD COLUMN shap_values JSONB;

COMMENT ON COLUMN churn.predictions.shap_values IS
    'Contribuições SHAP por feature. Estrutura: {"feature_name": valor_shap, ...}.
     Apenas top-N features (default: 5) para economizar espaço.
     Null quando SHAP não foi calculado (inferência online sem flag ativo).';

COMMIT;
