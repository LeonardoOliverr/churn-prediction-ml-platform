"""Shared settings and feature groups for ML training."""

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

# Columns excluded from training:
# - identifiers and infrastructure metadata
# - location fields with no baseline predictive value
# - churn_score: calculated from churn itself, which would leak target data
# - churn_reason/churn_label: only known after churn, which would leak target data
# - cltv: derived from tenure and charges; it does not add independent signal here
DROP_COLS = [
    "id",
    "tenant_id",
    "project_id",
    "customer_id",
    "customer_count",
    "country",
    "state",
    "city",
    "zip_code",
    "lat_long",
    "latitude",
    "longitude",
    "churn_label",
    "churn_score",
    "cltv",
    "churn_reason",
    "is_synthetic",
    "created_at",
    "split",
]
