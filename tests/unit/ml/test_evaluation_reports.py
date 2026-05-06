from types import SimpleNamespace

from ml.evaluation.comparison import CandidateResult, compare_results
from ml.evaluation.reports import build_run_report


def _candidate(name: str, f1: float) -> CandidateResult:
    return CandidateResult(
        spec=SimpleNamespace(name=name),
        run_id=f"run-{name}",
        metrics={
            "f1_mean": f1,
            "roc_auc_mean": 0.85,
            "recall_mean": 0.75,
            "precision_mean": 0.65,
        },
    )


def test_build_run_report_includes_best_model_and_metrics():
    comparison = compare_results([
        _candidate("dummy", 0.2),
        _candidate("logistic_regression", 0.7),
    ])

    report = build_run_report(
        comparison=comparison,
        experiment_name="global/baseline",
        tenant_slug=None,
        project_slug=None,
        holdout_size=0.2,
    )

    assert "Melhor modelo : logistic_regression" in report
    assert "F1            : 0.7000" in report
    assert "ROC-AUC       : 0.8500" in report
    assert "Candidatos secundarios:" in report


def test_build_run_report_works_with_single_model():
    comparison = compare_results([_candidate("random_forest", 0.8)])

    report = build_run_report(
        comparison=comparison,
        experiment_name="tenant/random-forest",
        tenant_slug="tenant",
        project_slug=None,
        holdout_size=0.0,
    )

    assert "Melhor modelo : random_forest" in report
    assert "Holdout       : desativado (CV puro)" in report
    assert "Candidatos secundarios:" not in report
