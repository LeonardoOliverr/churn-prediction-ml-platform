"""Model comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ml.core.model_spec import ModelSpec


@dataclass(frozen=True)
class CandidateResult:
    """Resultado de um modelo treinado dentro do run atual."""

    spec: ModelSpec
    run_id: str
    metrics: dict[str, float]
    hyperparameters: dict = field(default_factory=dict)
    training_params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RunComparison:
    """Decisao local do run sobre melhor modelo e candidatos secundarios."""

    best_candidate: CandidateResult
    secondary_candidates: list[CandidateResult]
    status_by_model: dict[str, str]
    candidates: list[CandidateResult]


def compare_results(
    candidates: list[CandidateResult],
    primary_metric: str = "f1_mean",
) -> RunComparison:
    """Seleciona o melhor candidato pela metrica primaria.

    Em caso de empate, vence o primeiro candidato na ordem recebida.
    """
    if not candidates:
        raise ValueError("E necessario informar ao menos um candidato para comparacao.")

    best_index = max(
        range(len(candidates)),
        key=lambda index: candidates[index].metrics[primary_metric],
    )
    best_candidate = candidates[best_index]
    secondary_candidates = [
        candidate for index, candidate in enumerate(candidates) if index != best_index
    ]
    status_by_model = {
        candidate.spec.name: "approved" if index == best_index else "trained"
        for index, candidate in enumerate(candidates)
    }

    return RunComparison(
        best_candidate=best_candidate,
        secondary_candidates=secondary_candidates,
        status_by_model=status_by_model,
        candidates=candidates,
    )
