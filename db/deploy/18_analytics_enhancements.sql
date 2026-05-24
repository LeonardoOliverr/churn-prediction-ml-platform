-- Deploy churn_prediction:18_analytics_enhancements to pg
-- requires: 17_comments
--
-- Adiciona métricas analíticas avançadas em evaluation_run_results:
--   - Taxas derivadas: FPR, FNR, especificidade
--   - Segmentação de risco: contagens por faixa de probabilidade
--   - Recomendação de promoção: candidato + justificativa
-- Cria view evaluation_comparison para delta vs champion.
-- Atualiza model_performance para incluir novas colunas.

BEGIN;

-- ---------------------------------------------------------------------------
-- A) Novas colunas em evaluation_run_results
-- ---------------------------------------------------------------------------

ALTER TABLE churn.evaluation_run_results
    -- Taxas derivadas
    ADD COLUMN false_positive_rate  NUMERIC(6,4),
    ADD COLUMN false_negative_rate  NUMERIC(6,4),
    ADD COLUMN specificity          NUMERIC(6,4),
    -- Segmentação de risco (contagens por faixa de churn_prob)
    ADD COLUMN high_risk_count      INTEGER,
    ADD COLUMN medium_risk_count    INTEGER,
    ADD COLUMN low_risk_count       INTEGER,
    -- Recomendação de promoção
    ADD COLUMN promotion_candidate  BOOLEAN,
    ADD COLUMN recommendation_reason TEXT;

COMMENT ON COLUMN churn.evaluation_run_results.false_positive_rate IS
    'Taxa de falsos positivos: FP / (FP + TN). Fração dos negativos reais que foram alertados incorretamente.';
COMMENT ON COLUMN churn.evaluation_run_results.false_negative_rate IS
    'Taxa de falsos negativos: FN / (FN + TP). Fração dos churns reais que o modelo perdeu.';
COMMENT ON COLUMN churn.evaluation_run_results.specificity IS
    'Especificidade: TN / (TN + FP). Taxa de acerto nos clientes que não churnam.';
COMMENT ON COLUMN churn.evaluation_run_results.high_risk_count IS
    'Predições com probabilidade de churn acima de 0.7 (alto risco). Requer churn_prob preenchido nas predições.';
COMMENT ON COLUMN churn.evaluation_run_results.medium_risk_count IS
    'Predições com probabilidade de churn entre 0.3 e 0.7 inclusive (risco médio).';
COMMENT ON COLUMN churn.evaluation_run_results.low_risk_count IS
    'Predições com probabilidade de churn abaixo de 0.3 (baixo risco).';
COMMENT ON COLUMN churn.evaluation_run_results.promotion_candidate IS
    'Indica se o modelo é candidato a promoção para champion com base nas métricas deste run.';
COMMENT ON COLUMN churn.evaluation_run_results.recommendation_reason IS
    'Justificativa textual da recomendação de promoção ou manutenção do status atual.';

-- ---------------------------------------------------------------------------
-- B) View evaluation_comparison — delta vs champion via self-join
-- ---------------------------------------------------------------------------

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
    -- Delta vs champion: NULL para o próprio champion
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

COMMENT ON VIEW churn.evaluation_comparison IS
    'Visão de comparação entre modelos em um mesmo run de avaliação. '
    'Calcula delta de F1, recall e custo do challenger em relação ao champion via self-join. '
    'Deltas são NULL para o próprio champion.';

-- ---------------------------------------------------------------------------
-- C) Renomear e expandir cost_analysis_v2 → model_performance
-- ---------------------------------------------------------------------------

DROP VIEW churn.cost_analysis_v2;

CREATE VIEW churn.model_performance AS
SELECT
    r.id,
    r.tenant_id,
    r.project_id,
    r.model_id,
    run.fp_cost                 AS false_positive_cost,
    run.fn_cost                 AS false_negative_cost,
    r.total_cost,
    r.threshold_used,
    r.tp,
    r.fp,
    r.fn,
    r.tn,
    r.precision_score,
    r.recall_score,
    r.f1_score,
    r.roc_auc,
    r.false_positive_rate,
    r.false_negative_rate,
    r.specificity,
    r.high_risk_count,
    r.medium_risk_count,
    r.low_risk_count,
    r.promotion_candidate,
    r.recommendation_reason,
    r.evaluated_predictions     AS total_predictions,
    run.period_start,
    run.period_end,
    run.evaluation_type,
    r.model_role_snapshot,
    r.model_name_snapshot,
    r.model_version_snapshot,
    r.created_at                AS evaluated_at,
    run.id                      AS evaluation_run_id
FROM churn.evaluation_run_results r
JOIN churn.evaluation_runs run ON run.id = r.evaluation_run_id;

COMMENT ON VIEW churn.model_performance IS
    'View de compatibilidade sobre evaluation_run_results (atualizada na migration 18). '
    'Inclui todas as métricas analíticas avançadas: taxas derivadas, segmentação de risco e recomendação de promoção. '
    'Use esta view para queries que referenciavam cost_analysis.';

COMMIT;
