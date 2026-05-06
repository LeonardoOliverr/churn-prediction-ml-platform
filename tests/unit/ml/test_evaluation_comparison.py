from types import SimpleNamespace

import pytest

from ml.evaluation.comparison import CandidateResult, compare_results


def _candidate(name: str, f1: float) -> CandidateResult:
    return CandidateResult(
        spec=SimpleNamespace(name=name),
        run_id=f"run-{name}",
        metrics={
            "f1_mean": f1,
            "roc_auc_mean": 0.8,
            "recall_mean": 0.7,
            "precision_mean": 0.6,
        },
    )


def test_compare_results_selects_highest_f1():
    comparison = compare_results([
        _candidate("dummy", 0.2),
        _candidate("logistic_regression", 0.7),
    ])

    assert comparison.best_candidate.spec.name == "logistic_regression"
    assert [c.spec.name for c in comparison.secondary_candidates] == ["dummy"]


def test_compare_results_assigns_statuses():
    comparison = compare_results([
        _candidate("dummy", 0.2),
        _candidate("logistic_regression", 0.7),
    ])

    assert comparison.status_by_model == {
        "dummy": "trained",
        "logistic_regression": "approved",
    }


def test_compare_results_tie_keeps_first_candidate():
    comparison = compare_results([
        _candidate("first", 0.7),
        _candidate("second", 0.7),
    ])

    assert comparison.best_candidate.spec.name == "first"
    assert comparison.status_by_model["first"] == "approved"
    assert comparison.status_by_model["second"] == "trained"


def test_compare_results_requires_candidates():
    with pytest.raises(ValueError):
        compare_results([])
