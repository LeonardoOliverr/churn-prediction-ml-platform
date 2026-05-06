"""Evaluation utilities for model metrics, reports, and comparisons."""

from ml.evaluation.comparison import CandidateResult, RunComparison, compare_results
from ml.evaluation.reports import build_run_report

__all__ = [
    "CandidateResult",
    "RunComparison",
    "build_run_report",
    "compare_results",
]
