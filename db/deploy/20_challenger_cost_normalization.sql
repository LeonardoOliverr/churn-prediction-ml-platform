-- Deploy churn_prediction:20_challenger_cost_normalization to pg
-- requires: 19_grafana_readonly
--
-- Adiciona colunas de custo normalizado em evaluation_run_results e recria
-- evaluation_comparison com métricas por predição, eliminando o bias de volume
-- na comparação champion vs challenger com splits de tráfego distintos.

BEGIN;

-- ---------------------------------------------------------------------------
-- A) Novas colunas em evaluation_run_results
-- ---------------------------------------------------------------------------

ALTER TABLE churn.evaluation_run_results
    ADD COLUMN cost_per_prediction  NUMERIC(12, 4),
    ADD COLUMN traffic_split_pct    NUMERIC(5, 2);

COMMENT ON COLUMN churn.evaluation_run_results.cost_per_prediction IS
    'Custo unitário por predição: total_cost / evaluated_predictions. '
    'Métrica normalizada para comparação justa entre champion (100% do tráfego) e challenger (fração do tráfego).';

COMMENT ON COLUMN churn.evaluation_run_results.traffic_split_pct IS
    'Percentual do tráfego recebido pelo modelo no momento da avaliação (ex: 20.00 para 20%). '
    'Derivado de project_model_config.traffic_split no momento do run.';

-- ---------------------------------------------------------------------------
-- B) Recriar evaluation_comparison com delta_cost_per_pred
-- ---------------------------------------------------------------------------

DROP VIEW churn.evaluation_comparison;

CREATE VIEW churn.evaluation_comparison AS
WITH champion_per_run AS (
    SELECT
        evaluation_run_id,
        project_id,
        f1_score            AS champ_f1,
        recall_score        AS champ_recall,
        total_cost          AS champ_cost,
        cost_per_prediction AS champ_cost_per_pred
    FROM churn.evaluation_run_results
    WHERE model_role_snapshot = 'champion'
)
SELECT
    r.*,
    -- Deltas de taxa (não sofrem bias de volume — mantidos intactos)
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.f1_score     - c.champ_f1,    4) END AS delta_f1,
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.recall_score - c.champ_recall, 4) END AS delta_recall,
    -- Custo bruto (mantido por compatibilidade — não usar para comparar modelos com splits diferentes)
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.total_cost - c.champ_cost, 2) END AS delta_cost,
    CASE WHEN r.model_role_snapshot <> 'champion' AND c.champ_cost > 0
         THEN ROUND((r.total_cost - c.champ_cost) / c.champ_cost * 100, 2) END AS delta_cost_pct,
    -- Custo normalizado por predição: comparação justa independente do split de tráfego
    CASE WHEN r.model_role_snapshot <> 'champion'
         THEN ROUND(r.cost_per_prediction - c.champ_cost_per_pred, 4) END AS delta_cost_per_pred,
    CASE WHEN r.model_role_snapshot <> 'champion' AND c.champ_cost_per_pred > 0
         THEN ROUND(
             (r.cost_per_prediction - c.champ_cost_per_pred) / c.champ_cost_per_pred * 100,
             2
         ) END AS delta_cost_per_pred_pct
FROM churn.evaluation_run_results r
LEFT JOIN champion_per_run c
       ON c.evaluation_run_id = r.evaluation_run_id
      AND c.project_id        = r.project_id;

COMMENT ON VIEW churn.evaluation_comparison IS
    'Comparação entre modelos em um mesmo run de avaliação via self-join. '
    'delta_cost_per_pred e delta_cost_per_pred_pct são as métricas corretas para comparar '
    'champion vs challenger quando os modelos processam volumes de tráfego diferentes. '
    'delta_cost e delta_cost_pct são mantidos por compatibilidade mas introduzem bias de volume. '
    'Todos os deltas são NULL para o próprio champion.';

COMMIT;
