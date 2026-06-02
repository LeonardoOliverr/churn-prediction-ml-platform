"""
Testes de schema usando pandera para validar estrutura e conteúdo dos DataFrames.
"""

import pandas as pd
import pandera as pa
import pytest

from ml.data.schema import processed_schema, raw_schema


@pytest.fixture
def sample_raw_df():
    """DataFrame mínimo válido representando o dataset bruto IBM Telco."""
    return pd.DataFrame(
        {
            "gender": ["Male", "Female"],
            "senior_citizen": [0, 1],
            "partner": ["Yes", "No"],
            "dependents": ["No", "Yes"],
            "tenure_months": [12, 36],
            "phone_service": ["Yes", "Yes"],
            "multiple_lines": ["No", "Yes"],
            "internet_service": ["DSL", "Fiber optic"],
            "online_security": ["No", "Yes"],
            "online_backup": ["Yes", "No"],
            "device_protection": ["No", "Yes"],
            "tech_support": ["No", "No"],
            "streaming_tv": ["No", "Yes"],
            "streaming_movies": ["Yes", "No"],
            "contract": ["Month-to-month", "Two year"],
            "paperless_billing": ["Yes", "No"],
            "payment_method": ["Electronic check", "Bank transfer (automatic)"],
            "monthly_charges": [29.85, 89.10],
            "total_charges": [358.20, 3210.60],
            "churn_value": [0, 1],
        }
    )


def test_raw_schema_valid_dataframe(sample_raw_df):
    """DataFrame válido passa no schema sem erros."""
    raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_negative_tenure(sample_raw_df):
    """tenure_months negativo levanta SchemaError."""
    sample_raw_df.loc[0, "tenure_months"] = -1
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_invalid_contract(sample_raw_df):
    """Valor de contract fora do domínio levanta SchemaError."""
    sample_raw_df.loc[0, "contract"] = "Weekly"
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_invalid_churn(sample_raw_df):
    """churn_value com valor diferente de 0 ou 1 levanta SchemaError."""
    sample_raw_df.loc[0, "churn_value"] = 2
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_raw_schema_nullable_total_charges(sample_raw_df):
    """total_charges pode ser nulo (clientes novos sem histórico de cobrança)."""
    sample_raw_df.loc[0, "total_charges"] = None
    raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_invalid_internet_service(sample_raw_df):
    """internet_service fora do domínio conhecido levanta SchemaError."""
    sample_raw_df.loc[0, "internet_service"] = "5G"
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_invalid_gender(sample_raw_df):
    """gender com valor fora do domínio levanta SchemaError."""
    sample_raw_df.loc[0, "gender"] = "Other"
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_tenure_above_72(sample_raw_df):
    """tenure_months acima de 72 viola o check de range de negócio."""
    sample_raw_df.loc[0, "tenure_months"] = 73
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_raw_schema_rejects_monthly_charges_out_of_range(sample_raw_df):
    """monthly_charges fora do range esperado (18–120) levanta SchemaError."""
    sample_raw_df.loc[0, "monthly_charges"] = 150.0
    with pytest.raises(pa.errors.SchemaError):
        raw_schema.validate(sample_raw_df)


def test_processed_schema_valid_dataframe():
    """DataFrame processado válido (somente floats, sem nulos) passa no schema."""
    df = pd.DataFrame(
        {
            "senior_citizen": [0.0, 1.0],
            "tenure_months": [0.5, -0.3],
            "monthly_charges": [-0.8, 1.2],
            "total_charges": [0.1, 0.9],
            "gender_Male": [1.0, 0.0],
            "partner_Yes": [1.0, 0.0],
            "dependents_Yes": [0.0, 1.0],
            "phone_service_Yes": [1.0, 1.0],
            "paperless_billing_Yes": [1.0, 0.0],
        }
    )
    processed_schema.validate(df)


def test_processed_schema_rejects_nulls():
    """DataFrame processado com nulos levanta SchemaError."""
    df = pd.DataFrame(
        {
            "senior_citizen": [0.0, None],
            "tenure_months": [0.5, -0.3],
            "monthly_charges": [-0.8, 1.2],
            "total_charges": [0.1, 0.9],
            "gender_Male": [1.0, 0.0],
            "partner_Yes": [1.0, 0.0],
            "dependents_Yes": [0.0, 1.0],
            "phone_service_Yes": [1.0, 1.0],
            "paperless_billing_Yes": [1.0, 0.0],
        }
    )
    with pytest.raises(pa.errors.SchemaError):
        processed_schema.validate(df)
