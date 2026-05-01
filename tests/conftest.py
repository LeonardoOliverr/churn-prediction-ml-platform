"""
Fixtures compartilhadas entre todos os testes do projeto.
"""

import pandas as pd
import pytest


@pytest.fixture
def fake_customers_df() -> pd.DataFrame:
    """DataFrame mínimo representando o IBM Telco Dataset.

    Contém 12 linhas balanceadas (6 churn=0, 6 churn=1) para suportar
    StratifiedKFold com n_splits=5 nos testes de baseline.
    Cobre todos os grupos de features: NUMERIC, BOOL e CATEGORICAL.
    """
    return pd.DataFrame(
        {
            # NUMERIC_FEATURES
            "tenure_months": [12, 24, 1, 60, 36, 48, 5, 72, 18, 30, 3, 55],
            "monthly_charges": [29.85, 56.95, 53.85, 42.30, 70.70, 99.65, 45.20, 79.85, 55.00, 65.60, 35.00, 88.15],
            "total_charges": [358.20, 1367.00, 53.85, 2537.00, 2535.00, 4789.00, 226.00, 5765.00, 990.00, 1968.00, 105.00, 4848.00],
            # BOOL_FEATURES
            "senior_citizen": [0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1],
            "partner": [1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1],
            "dependents": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
            "phone_service": [0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1],
            "paperless_billing": [1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0],
            # CATEGORICAL_FEATURES
            "gender": ["Female", "Male", "Male", "Female", "Male", "Female", "Male", "Female", "Male", "Female", "Male", "Female"],
            "multiple_lines": ["No", "Yes", "No", "Yes", "Yes", "No", "No", "Yes", "No", "Yes", "No", "Yes"],
            "internet_service": ["DSL", "Fiber optic", "DSL", "Fiber optic", "DSL", "Fiber optic", "DSL", "Fiber optic", "No", "DSL", "Fiber optic", "DSL"],
            "online_security": ["No", "No", "Yes", "No", "Yes", "No", "Yes", "No", "No internet service", "Yes", "No", "Yes"],
            "online_backup": ["Yes", "No", "Yes", "No", "Yes", "No", "No", "Yes", "No internet service", "No", "Yes", "No"],
            "device_protection": ["No", "Yes", "No", "Yes", "No", "Yes", "Yes", "No", "No internet service", "Yes", "No", "Yes"],
            "tech_support": ["No", "No", "No", "Yes", "Yes", "No", "No", "Yes", "No internet service", "No", "No", "Yes"],
            "streaming_tv": ["No", "Yes", "No", "Yes", "No", "Yes", "No", "Yes", "No internet service", "No", "Yes", "No"],
            "streaming_movies": ["No", "No", "No", "Yes", "Yes", "No", "No", "Yes", "No internet service", "Yes", "No", "Yes"],
            "contract": ["Month-to-month", "One year", "Month-to-month", "Two year", "One year", "Month-to-month", "Month-to-month", "Two year", "One year", "Month-to-month", "Month-to-month", "Two year"],
            "payment_method": ["Electronic check", "Mailed check", "Electronic check", "Bank transfer (automatic)", "Credit card (automatic)", "Electronic check", "Mailed check", "Bank transfer (automatic)", "Electronic check", "Mailed check", "Electronic check", "Credit card (automatic)"],
            # TARGET
            "churn_value": [0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0],
        }
    )
