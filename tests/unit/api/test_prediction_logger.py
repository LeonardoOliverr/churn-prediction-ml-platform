"""
Testes unitários para src/services/prediction_logger.py.

Cobre o caminho feliz (INSERT bem-sucedido) e o caminho de erro
(exceção é capturada sem relançar — o log nunca deve impactar a resposta).
"""

from unittest.mock import MagicMock, patch

from src.services.prediction_logger import log_prediction_bg


def _call(engine, raise_on_execute=False):
    if raise_on_execute:
        engine.begin.return_value.__enter__.return_value.execute.side_effect = Exception("DB offline")
    log_prediction_bg(
        engine=engine,
        prediction_id="pred-uuid",
        tenant_id="tenant-uuid",
        project_id="project-uuid",
        customer_id="CUST-1",
        model_id="model-uuid",
        churn_prob=0.82,
        churn_pred=True,
        threshold_used=0.5,
        latency_ms=42,
    )


def test_log_prediction_bg_executes_insert():
    """Chamada bem-sucedida executa INSERT em churn.predictions."""
    engine = MagicMock()
    mock_conn = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    _call(engine)

    mock_conn.execute.assert_called_once()
    params = mock_conn.execute.call_args[0][1]
    assert params["id"] == "pred-uuid"
    assert params["churn_prob"] == round(0.82, 4)


def test_log_prediction_bg_rounds_probability():
    """churn_prob é arredondado a 4 casas antes de ser inserido."""
    engine = MagicMock()
    mock_conn = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    log_prediction_bg(
        engine=engine,
        prediction_id="p", tenant_id="t", project_id="pr",
        customer_id="c", model_id="m",
        churn_prob=0.123456789,
        churn_pred=False,
        threshold_used=0.5,
        latency_ms=10,
    )

    params = mock_conn.execute.call_args[0][1]
    assert params["churn_prob"] == round(0.123456789, 4)


def test_log_prediction_bg_swallows_exception():
    """Exceção no INSERT é capturada silenciosamente — não relança."""
    engine = MagicMock()
    engine.begin.return_value.__enter__ = MagicMock(
        side_effect=Exception("DB offline")
    )
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    # Não deve levantar — falha no log é silenciosa
    _call(engine)
