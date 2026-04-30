"""
Constantes compartilhadas entre os módulos de treinamento.
"""

import os

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

TARGET = "churn_value"

NUMERIC_FEATURES = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
]

BOOL_FEATURES = [
    "senior_citizen",
    "partner",
    "dependents",
    "phone_service",
    "paperless_billing",
]

CATEGORICAL_FEATURES = [
    "gender",
    "multiple_lines",
    "internet_service",
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
    "contract",
    "payment_method",
]

# Colunas excluídas do treinamento:
# - Identificadores e metadados de infra
# - Localização (granularidade sem valor preditivo no baseline)
# - churn_score: calculado pelo IBM SPSS com base no próprio churn — data leakage
# - churn_reason / churn_label: só existem para clientes que cancelaram — data leakage
# - cltv: derivado de tenure + charges, não agrega sinal independente no baseline
DROP_COLS = [
    "id", "tenant_id", "project_id",
    "customer_id", "customer_count",
    "country", "state", "city", "zip_code", "lat_long", "latitude", "longitude",
    "churn_label", "churn_score", "cltv", "churn_reason",
    "is_synthetic", "created_at",
]
