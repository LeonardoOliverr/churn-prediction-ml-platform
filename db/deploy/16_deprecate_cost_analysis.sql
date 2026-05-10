-- Deploy churn_prediction:16_deprecate_cost_analysis to pg
-- requires: 15_evaluation_runs
--
-- cost_analysis foi substituída por evaluation_runs + evaluation_run_results
-- (migration 15). Esta migration marca a tabela como deprecated e cria uma
-- view de compatibilidade para queries existentes não quebrarem.

BEGIN;

COMMENT ON TABLE churn.cost_analysis IS
    'DEPRECATED desde migration 16. '
    'Substituída por churn.evaluation_runs + churn.evaluation_run_results. '
    'Mantida para compatibilidade com queries históricas. Não inserir novos dados.';

-- View de compatibilidade: expõe evaluation_run_results com o schema antigo
-- de cost_analysis para facilitar migração de queries existentes.
CREATE VIEW churn.cost_analysis_v2 AS
SELECT
    r.id,
    r.tenant_id,
    r.project_id,
    r.model_id,
    run.fp_cost          AS false_positive_cost,
    run.fn_cost          AS false_negative_cost,
    r.total_cost,
    r.threshold_used,
    r.tp,
    r.fp,
    r.fn,
    r.tn,
    r.precision_score,
    r.recall_score,
    r.f1_score,
    r.evaluated_predictions AS total_predictions,
    run.period_start,
    run.period_end,
    run.evaluation_type,
    r.model_role_snapshot,
    r.model_name_snapshot,
    r.model_version_snapshot,
    r.created_at         AS evaluated_at,
    run.id               AS evaluation_run_id
FROM churn.evaluation_run_results r
JOIN churn.evaluation_runs run ON run.id = r.evaluation_run_id;

COMMENT ON VIEW churn.cost_analysis_v2 IS
    'View de compatibilidade sobre evaluation_run_results. '
    'Use esta view para queries que referenciavam cost_analysis. '
    'Inclui model_role_snapshot e evaluation_run_id adicionais.';

COMMIT;
