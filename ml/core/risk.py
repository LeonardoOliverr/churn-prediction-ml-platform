"""
Regra de classificação de risco de churn baseada em probabilidade prevista.
"""


def classify_risk(
    probability: float,
    threshold_low: float = 0.4,
    threshold_high: float = 0.8,
) -> str:
    """Classifica o risco de churn com base na probabilidade prevista.

    Args:
        probability: Probabilidade de churn prevista pelo modelo (0.0 a 1.0).
        threshold_low: Limite inferior para risco médio (padrão: 0.4).
        threshold_high: Limite para risco alto (padrão: 0.8).

    Returns:
        "high" se probability >= threshold_high,
        "medium" se probability >= threshold_low,
        "low" caso contrário.

    Raises:
        ValueError: Se probability estiver fora do intervalo [0.0, 1.0].
    """
    if not (0.0 <= probability <= 1.0):
        raise ValueError(
            f"Probabilidade deve estar entre 0.0 e 1.0. Recebido: {probability}"
        )
    if probability >= threshold_high:
        return "high"
    if probability >= threshold_low:
        return "medium"
    return "low"
