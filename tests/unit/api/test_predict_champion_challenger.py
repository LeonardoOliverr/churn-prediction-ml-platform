"""
Testes unitários da inferência com roteamento por cliente no batch.
"""

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from fastapi import BackgroundTasks

from src.middleware.auth import ApiKeyRecord
from src.routers.predict import predict_batch
from src.schemas.predict import BatchPredictRequest, CustomerFeatures


class _Pipeline:
    """Pipeline fake com probabilidade fixa."""

    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, X):
        return np.array([[1 - self.probability, self.probability] for _ in range(len(X))])


def _customer(row, customer_id: str) -> CustomerFeatures:
    """Cria CustomerFeatures a partir de uma linha fake."""
    payload = row.drop(labels=["churn_value"]).to_dict()
    payload["customer_id"] = customer_id
    return CustomerFeatures(**payload)


def test_predict_batch_preserves_order_with_different_models(fake_customers_df):
    """Batch preserva ordem mesmo quando clientes usam modelos diferentes."""
    first = _customer(fake_customers_df.iloc[0], "CUST-A")
    second = _customer(fake_customers_df.iloc[1], "CUST-B")
    batch = BatchPredictRequest(customers=[first, second])
    request = MagicMock()
    request.state = SimpleNamespace()
    api_key = ApiKeyRecord(id="key-1", tenant_id="tenant-1", project_id="project-1", scopes=["predict"], key_prefix="prefix")
    settings = SimpleNamespace(max_batch_size=100)

    champion_loaded = (_Pipeline(0.1), 0.5, {"id": "champion-id", "version": "v1", "name": "champion", "project_id": "project-1"})
    challenger_loaded = (_Pipeline(0.9), 0.5, {"id": "challenger-id", "version": "v1", "name": "challenger", "project_id": "project-1"})

    def _choose_for_customer(**kwargs):
        if kwargs["customer_id"] == "CUST-A":
            return champion_loaded
        return challenger_loaded

    with patch("src.routers.predict.resolve_batch_models", return_value=(champion_loaded, challenger_loaded)), \
         patch("src.routers.predict.choose_for_customer", side_effect=_choose_for_customer), \
         patch("src.routers.predict._get_engine", return_value=object()):
        response = inspect.unwrap(predict_batch)(
            request=request,
            batch=batch,
            background_tasks=BackgroundTasks(),
            db=MagicMock(),
            api_key=api_key,
            settings=settings,
        )

    assert [item.customer_id for item in response.results] == ["CUST-A", "CUST-B"]
    assert [item.model_id for item in response.results] == ["champion-id", "challenger-id"]
