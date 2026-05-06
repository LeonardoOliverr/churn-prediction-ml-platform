"""Evaluation report builders."""

from __future__ import annotations

from ml.evaluation.comparison import RunComparison


def _scope_label(tenant_slug: str | None, project_slug: str | None) -> tuple[str, str, str]:
    return (
        tenant_slug or "-",
        project_slug or "-",
        "project" if project_slug else "tenant" if tenant_slug else "global",
    )


def build_run_report(
    comparison: RunComparison,
    experiment_name: str,
    tenant_slug: str | None,
    project_slug: str | None,
    holdout_size: float,
) -> str:
    """Gera um resumo textual da decisao local do run."""
    tenant_label, project_label, scope = _scope_label(tenant_slug, project_slug)
    best = comparison.best_candidate
    metrics = best.metrics
    holdout_label = (
        f"{holdout_size:.0%} reservado para avaliacao final"
        if holdout_size > 0
        else "desativado (CV puro)"
    )

    lines = [
        "",
        "=" * 50,
        "Resumo do run",
        f"Escopo        : {scope}",
        f"Tenant        : {tenant_label}",
        f"Projeto       : {project_label}",
        f"Experimento   : {experiment_name}",
        f"Holdout       : {holdout_label}",
        f"Melhor modelo : {best.spec.name}",
        f"F1            : {metrics['f1_mean']:.4f}",
        f"ROC-AUC       : {metrics['roc_auc_mean']:.4f}",
        f"Recall        : {metrics['recall_mean']:.4f}",
        f"Precision     : {metrics['precision_mean']:.4f}",
        "=" * 50,
    ]

    if comparison.secondary_candidates:
        lines.append("Candidatos secundarios:")
        for candidate in comparison.secondary_candidates:
            candidate_metrics = candidate.metrics
            lines.append(
                f"  {candidate.spec.name}: "
                f"F1={candidate_metrics['f1_mean']:.4f} | "
                f"ROC-AUC={candidate_metrics['roc_auc_mean']:.4f}"
            )

    return "\n".join(lines)
