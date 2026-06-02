"""Schemas pandera para validação declarativa dos DataFrames do pipeline de ML."""

import pandera as pa

# Schema para o DataFrame bruto (pós-ingestão, pré-preprocessing)
raw_schema = pa.DataFrameSchema(
    columns={
        "senior_citizen": pa.Column(int, pa.Check.isin([0, 1])),
        "tenure_months": pa.Column(int, pa.Check.ge(0)),
        "monthly_charges": pa.Column(float, pa.Check.gt(0)),
        "total_charges": pa.Column(float, pa.Check.ge(0), nullable=True),
        "gender": pa.Column(str, pa.Check.isin(["Male", "Female"])),
        "contract": pa.Column(str, pa.Check.isin(["Month-to-month", "One year", "Two year"])),
        "internet_service": pa.Column(str, pa.Check.isin(["DSL", "Fiber optic", "No"])),
        "payment_method": pa.Column(str),
        "churn_value": pa.Column(int, pa.Check.isin([0, 1])),
    },
    checks=[
        pa.Check(
            lambda df: df["tenure_months"].between(0, 72).all(),
            error="tenure_months fora do range esperado (0–72)",
        ),
        pa.Check(
            lambda df: df["monthly_charges"].between(18, 120).all(),
            error="monthly_charges fora do range esperado (18–120)",
        ),
    ],
    coerce=True,
)

# Schema para o DataFrame processado (pós-preprocessing, pré-treinamento)
processed_schema = pa.DataFrameSchema(
    columns={
        col: pa.Column(float)
        for col in [
            "senior_citizen",
            "tenure_months",
            "monthly_charges",
            "total_charges",
            "gender_Male",
            "partner_Yes",
            "dependents_Yes",
            "phone_service_Yes",
            "paperless_billing_Yes",
        ]
    },
    checks=[
        pa.Check(
            lambda df: df.isnull().sum().sum() == 0,
            error="Features com nulos após preprocessing",
        ),
    ],
)
