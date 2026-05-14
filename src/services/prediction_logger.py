"""
Log assíncrono de predições em churn.predictions.

Deve ser chamado exclusivamente via FastAPI BackgroundTasks, pois roda após
o response já ter sido enviado. Por isso, recebe o engine (não uma Connection)
e abre sua própria transação para evitar uso de conexão fechada do request.
"""

import structlog
from sqlalchemy import text

logger = structlog.get_logger()

_INSERT_SQL = text("""
    INSERT INTO churn.predictions
        (id, tenant_id, project_id, customer_id, model_id,
         churn_prob, churn_pred, threshold_used, latency_ms)
    VALUES
        (:id, :tenant_id, :project_id, :customer_id, :model_id,
         :churn_prob, :churn_pred, :threshold_used, :latency_ms)
""")


def log_prediction_bg(
    engine,
    prediction_id: str,
    tenant_id: str,
    project_id: str,
    customer_id: str,
    model_id: str,
    churn_prob: float,
    churn_pred: bool,
    threshold_used: float,
    latency_ms: int,
) -> None:
    """Insere registro de predição em churn.predictions com conexão própria."""
    try:
        with engine.begin() as conn:
            conn.execute(
                _INSERT_SQL,
                {
                    "id": prediction_id,
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "customer_id": customer_id,
                    "model_id": model_id,
                    "churn_prob": round(churn_prob, 4),
                    "churn_pred": churn_pred,
                    "threshold_used": round(threshold_used, 3),
                    "latency_ms": latency_ms,
                },
            )
    except Exception as exc:
        # Falha no log não deve impactar a resposta já enviada ao cliente
        logger.error("prediction_log_failed", customer_id=customer_id, error=str(exc))
