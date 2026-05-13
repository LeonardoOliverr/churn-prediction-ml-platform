"""Business rule for classifying churn risk from model probability."""

from domain.constants import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_LOW, RiskLevel


def classify_risk(
    probability: float,
    threshold_low: float = RISK_THRESHOLD_LOW,
    threshold_high: float = RISK_THRESHOLD_HIGH,
) -> RiskLevel:
    """Classify churn risk as low, medium, or high."""
    if not (0.0 <= probability <= 1.0):
        raise ValueError(
            f"Probabilidade deve estar entre 0.0 e 1.0. Recebido: {probability}"
        )
    if probability >= threshold_high:
        return RiskLevel.HIGH
    if probability >= threshold_low:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
