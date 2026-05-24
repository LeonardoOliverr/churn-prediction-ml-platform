-- Revert churn_prediction:20_challenger_cost_normalization from pg

BEGIN;

-- Recriar evaluation_comparison sem as colunas normalizadas
DROP VIEW IF EXISTS churn.evaluation_comparison;

CREATE VIEW churn.evaluation_comparison AS
WITH champion_per_run AS (
    SELECT
        evaluation_run_id,
        project_id,
        f1_score     AS champ_f1,
        recall_score AS champ_recall,
        total_cost   AS champ_cost
    FROM churn.evaluation_run_results
    WHERE model_role_snapshot = 'champion'
)
SELECT
    r.*,
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.f1_score     - c.champ_f1,    4) END AS delta_f1,
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.recall_score - c.champ_recall, 4) END AS delta_recall,
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.total_cost   - c.champ_cost,   2) END AS delta_cost,
    CASE WHEN r.model_role_snapshot <> 'champion' AND c.champ_cost > 0
         THEN ROUND((r.total_cost - c.champ_cost) / c.champ_cost * 100, 2) END AS delta_cost_pct
FROM churn.evaluation_run_results r
LEFT JOIN champion_per_run c
       ON c.evaluation_run_id = r.evaluation_run_id
      AND c.project_id        = r.project_id;

-- Remover colunas adicionadas nesta migration
ALTER TABLE churn.evaluation_run_results
    DROP COLUMN IF EXISTS cost_per_prediction,
    DROP COLUMN IF EXISTS traffic_split_pct;

COMMIT;
