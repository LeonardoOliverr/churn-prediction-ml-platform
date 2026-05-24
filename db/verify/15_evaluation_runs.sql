-- Verify churn_prediction:15_evaluation_runs on pg

SELECT id, tenant_id, project_id, period_start, period_end,
       evaluation_type, fp_cost, fn_cost, triggered_by, status,
       created_at, completed_at, metadata
  FROM churn.evaluation_runs
 WHERE FALSE;

SELECT id, evaluation_run_id, tenant_id, project_id, model_id,
       model_name_snapshot, model_version_snapshot, model_role_snapshot,
       traffic_split_snapshot, threshold_used,
       tp, fp, fn, tn,
       precision_score, recall_score, f1_score, roc_auc,
       fp_cost, fn_cost, total_cost,
       evaluated_predictions, missing_actual_labels,
       created_at, metadata
  FROM churn.evaluation_run_results
 WHERE FALSE;
