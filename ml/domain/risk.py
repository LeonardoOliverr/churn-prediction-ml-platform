"""Business rule for classifying churn risk from model probability."""


def classify_risk(
    probability: float,
    threshold_low: float = 0.4,
    threshold_high: float = 0.8,
) -> str:
    """Classify churn risk as low, medium, or high."""
    if not (0.0 <= probability <= 1.0):
        raise ValueError(
            f"Probabilidade deve estar entre 0.0 e 1.0. Recebido: {probability}"
        )
    if probability >= threshold_high:
        return "high"
    if probability >= threshold_low:
        return "medium"
    return "low"
