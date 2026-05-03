"""
Schemas de entrada e saída dos endpoints de inferência.

A ordem dos campos em CustomerFeatures deve seguir exatamente ml/config.py
para garantir que o DataFrame gerado tenha as colunas na ordem esperada pelo pipeline.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_CUSTOMER_EXAMPLE = {
    "customer_id": "CUST-8301",
    "tenure_months": 2,
    "monthly_charges": 94.5,
    "total_charges": 189.0,
    "senior_citizen": 0,
    "partner": 0,
    "dependents": 0,
    "phone_service": 1,
    "paperless_billing": 1,
    "gender": "Male",
    "multiple_lines": "No",
    "internet_service": "Fiber optic",
    "online_security": "No",
    "online_backup": "No",
    "device_protection": "No",
    "tech_support": "No",
    "streaming_tv": "No",
    "streaming_movies": "No",
    "contract": "Month-to-month",
    "payment_method": "Electronic check",
}


class CustomerFeatures(BaseModel):
    """Features do cliente enviadas para predição. Espelha os grupos definidos em ml/config.py."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": _CUSTOMER_EXAMPLE,
        }
    )

    customer_id: str = Field(..., description="Identificador único do cliente no sistema de origem.")

    # NUMERIC_FEATURES — ml/config.py
    tenure_months: float = Field(..., description="Meses de contrato ativo.")
    monthly_charges: float = Field(..., description="Valor mensal da fatura (USD).")
    total_charges: float = Field(..., description="Total histórico cobrado (USD).")

    # BOOL_FEATURES — ml/config.py (aceita 0/1)
    senior_citizen: int = Field(..., ge=0, le=1, description="`1` se o cliente é sênior (65+).")
    partner: int = Field(..., ge=0, le=1, description="`1` se possui cônjuge.")
    dependents: int = Field(..., ge=0, le=1, description="`1` se possui dependentes.")
    phone_service: int = Field(..., ge=0, le=1, description="`1` se possui serviço telefônico.")
    paperless_billing: int = Field(..., ge=0, le=1, description="`1` se recebe fatura digital.")

    # CATEGORICAL_FEATURES — ml/config.py
    gender: str = Field(..., description='`"Male"` ou `"Female"`.')
    multiple_lines: str = Field(..., description='`"No"` | `"Yes"` | `"No phone service"`.')
    internet_service: str = Field(..., description='`"DSL"` | `"Fiber optic"` | `"No"`.')
    online_security: str = Field(..., description='`"No"` | `"Yes"` | `"No internet service"`.')
    online_backup: str = Field(..., description='`"No"` | `"Yes"` | `"No internet service"`.')
    device_protection: str = Field(..., description='`"No"` | `"Yes"` | `"No internet service"`.')
    tech_support: str = Field(..., description='`"No"` | `"Yes"` | `"No internet service"`.')
    streaming_tv: str = Field(..., description='`"No"` | `"Yes"` | `"No internet service"`.')
    streaming_movies: str = Field(..., description='`"No"` | `"Yes"` | `"No internet service"`.')
    contract: str = Field(..., description='`"Month-to-month"` | `"One year"` | `"Two year"`.')
    payment_method: str = Field(
        ...,
        description='`"Electronic check"` | `"Mailed check"` | `"Bank transfer (automatic)"` | `"Credit card (automatic)"`.',
    )


class PredictResponse(BaseModel):
    """Resposta do endpoint POST /predict. Contrato validado em tests/api/test_predict_contract.py."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prediction_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "customer_id": "CUST-8301",
                "churn_probability": 0.8341,
                "risk_level": "high",
                "churn_pred": True,
                "threshold_used": 0.5,
                "model_version": "1",
                "model_name": "LogisticRegression",
                "model_id": "9b2e1f3a-4c8d-4e1b-b5a7-1f2e3d4c5b6a",
            }
        }
    )

    prediction_id: str = Field(..., description="UUID gerado para esta predição (usado para rastreamento).")
    customer_id: str = Field(..., description="Identificador do cliente enviado na requisição.")
    churn_probability: float = Field(..., description="Probabilidade de churn — valor entre 0.0 e 1.0.")
    risk_level: Literal["low", "medium", "high"] = Field(
        ..., description='Classificação de risco: `low` (< 0.3) | `medium` (0.3–0.7) | `high` (> 0.7).'
    )
    churn_pred: bool = Field(..., description='`true` se `churn_probability >= threshold_used`.')
    threshold_used: float = Field(..., description="Threshold de decisão aplicado (definido em `project_model_config`).")
    model_version: str = Field(..., description="Versão do modelo no MLflow Model Registry.")
    model_name: str = Field(..., description="Nome do algoritmo registrado (ex.: `LogisticRegression`).")
    model_id: str = Field(..., description="UUID do modelo em `churn.models`.")


class BatchPredictRequest(BaseModel):
    """Requisição de predição em lote. Tamanho máximo definido por MAX_BATCH_SIZE."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customers": [
                    _CUSTOMER_EXAMPLE,
                    {
                        **_CUSTOMER_EXAMPLE,
                        "customer_id": "CUST-1042",
                        "tenure_months": 58,
                        "monthly_charges": 45.0,
                        "total_charges": 2610.0,
                        "partner": 1,
                        "dependents": 1,
                        "paperless_billing": 0,
                        "gender": "Female",
                        "multiple_lines": "Yes",
                        "internet_service": "DSL",
                        "online_security": "Yes",
                        "online_backup": "Yes",
                        "device_protection": "Yes",
                        "tech_support": "Yes",
                        "contract": "Two year",
                        "payment_method": "Bank transfer (automatic)",
                    },
                ]
            }
        }
    )

    customers: list[CustomerFeatures] = Field(..., description="Lista de clientes para predição em lote (máx. 100).")


class BatchPredictResponse(BaseModel):
    """Resposta de predição em lote com resultados e total processado."""

    results: list[PredictResponse] = Field(..., description="Predições na mesma ordem dos clientes enviados.")
    total: int = Field(..., description="Número total de predições retornadas.")


class PredictionRecord(BaseModel):
    """Registro histórico de uma predição armazenada em churn.predictions."""

    id: str = Field(..., description="UUID da predição.")
    customer_id: str
    churn_probability: float
    churn_pred: bool
    threshold_used: float
    latency_ms: int | None = Field(None, description="Latência de inferência em milissegundos.")
    requested_at: str = Field(..., description="Timestamp UTC da predição.")
    model_id: str


class PredictionsListResponse(BaseModel):
    """Resposta paginada do endpoint GET /predictions."""

    items: list[PredictionRecord]
    total: int = Field(..., description="Total de predições no filtro (sem paginação).")
    page: int
    page_size: int
