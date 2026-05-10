"""
Testes unitários para pipeline/load_ibm_telco.py.

Cobre transform() — lógica pura de transformação sem banco de dados — e
load() com mock de engine. fetch_dataset() e resolve_ids() requerem
Kaggle e PostgreSQL e ficam reservados para testes de integração.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from pipeline.load_ibm_telco import COLUMN_MAP, YES_NO_COLS, load, transform


# ---------------------------------------------------------------------------
# Fixture: DataFrame raw com colunas originais do IBM Telco (pré-transform)
# ---------------------------------------------------------------------------


@pytest.fixture
def raw_telco_df() -> pd.DataFrame:
    """DataFrame mínimo com os nomes originais de coluna do IBM Telco."""
    return pd.DataFrame(
        {
            "CustomerID": ["7590-VHVEG", "5575-GNVDE", "3668-QPYBK"],
            "Count": [1, 1, 1],
            "Country": ["United States"] * 3,
            "State": ["California"] * 3,
            "City": ["Los Angeles", "San Diego", "Sacramento"],
            "Zip Code": [90001, 90002, 95801],
            "Lat Long": ["34.05 -118.24", "32.72 -117.15", "38.58 -121.49"],
            "Latitude": [34.05, 32.72, 38.58],
            "Longitude": [-118.24, -117.15, -121.49],
            "Gender": ["Female", "Male", "Male"],
            "Senior Citizen": ["No", "No", "No"],
            "Partner": ["Yes", "No", "No"],
            "Dependents": ["No", "No", "Yes"],
            "Tenure Months": [12, 24, 2],
            "Phone Service": ["No", "Yes", "Yes"],
            "Multiple Lines": ["No phone service", "No", "No"],
            "Internet Service": ["DSL", "DSL", "Fiber optic"],
            "Online Security": ["No", "Yes", "No"],
            "Online Backup": ["Yes", "No", "Yes"],
            "Device Protection": ["No", "Yes", "No"],
            "Tech Support": ["No", "No", "No"],
            "Streaming TV": ["No", "No", "Yes"],
            "Streaming Movies": ["No", "No", "No"],
            "Contract": ["Month-to-month", "One year", "Month-to-month"],
            "Paperless Billing": ["Yes", "No", "Yes"],
            "Payment Method": ["Electronic check", "Mailed check", "Mailed check"],
            "Monthly Charges": [29.85, 56.95, 53.85],
            "Total Charges": ["358.20", "1367.00", "108.15"],
            "Churn Label": ["No", "No", "Yes"],
            "Churn Value": [0, 0, 1],
            "Churn Score": [26, 85, 65],
            "CLTV": [3467, 5678, 3239],
            "Churn Reason": [None, None, "Competitor made better offer"],
        }
    )


# ---------------------------------------------------------------------------
# transform() — renomeação de colunas
# ---------------------------------------------------------------------------


def test_transform_renames_all_columns_to_snake_case(raw_telco_df):
    """Todas as colunas originais são renomeadas para snake_case via COLUMN_MAP."""
    df = transform(raw_telco_df)
    for original, renamed in COLUMN_MAP.items():
        assert renamed in df.columns, f"Coluna renomeada '{renamed}' ausente."
        assert original not in df.columns, f"Coluna original '{original}' ainda presente."


def test_transform_row_count_unchanged(raw_telco_df):
    """O número de linhas não muda após transform."""
    df = transform(raw_telco_df)
    assert len(df) == len(raw_telco_df)


# ---------------------------------------------------------------------------
# transform() — conversão Yes/No → bool
# ---------------------------------------------------------------------------


def test_transform_yes_maps_to_true(raw_telco_df):
    """'Yes' é mapeado para True nas colunas Yes/No."""
    df = transform(raw_telco_df)
    # Partner: primeira linha é "Yes"
    assert df["partner"].iloc[0] == True


def test_transform_no_maps_to_false(raw_telco_df):
    """'No' é mapeado para False nas colunas Yes/No."""
    df = transform(raw_telco_df)
    # Partner: segunda linha é "No"
    assert df["partner"].iloc[1] == False


def test_transform_all_yes_no_columns_converted(raw_telco_df):
    """Todas as colunas de YES_NO_COLS contêm apenas True, False ou NaN."""
    df = transform(raw_telco_df)
    for col in YES_NO_COLS:
        snake = COLUMN_MAP[col]
        unique = set(df[snake].dropna().unique())
        assert unique.issubset({True, False}), (
            f"Coluna '{snake}' contém valores inesperados: {unique}"
        )


def test_transform_strips_whitespace_before_mapping(raw_telco_df):
    """Espaços em torno de 'Yes' e 'no' são removidos antes do mapeamento."""
    raw_telco_df.loc[0, "Senior Citizen"] = "  Yes  "
    raw_telco_df.loc[1, "Senior Citizen"] = " no "
    df = transform(raw_telco_df)
    assert df["senior_citizen"].iloc[0] == True
    assert df["senior_citizen"].iloc[1] == False


def test_transform_unknown_yes_no_value_becomes_nan(raw_telco_df):
    """Valor desconhecido em coluna Yes/No resulta em NaN (não quebra)."""
    raw_telco_df.loc[0, "Partner"] = "Maybe"
    df = transform(raw_telco_df)
    assert pd.isna(df["partner"].iloc[0])


# ---------------------------------------------------------------------------
# transform() — Zip Code
# ---------------------------------------------------------------------------


def test_transform_zip_code_is_string(raw_telco_df):
    """Zip Code é convertido para string para evitar ser tratado como inteiro."""
    df = transform(raw_telco_df)
    assert df["zip_code"].dtype == object, "zip_code deveria ser dtype object (string)."


def test_transform_zip_code_value_preserved(raw_telco_df):
    """O valor numérico do Zip Code é preservado como string."""
    df = transform(raw_telco_df)
    assert df["zip_code"].iloc[0] == "90001"


# ---------------------------------------------------------------------------
# transform() — Total Charges
# ---------------------------------------------------------------------------


def test_transform_total_charges_numeric_string_converted(raw_telco_df):
    """Strings numéricas em Total Charges são convertidas para float."""
    df = transform(raw_telco_df)
    assert pd.api.types.is_numeric_dtype(df["total_charges"])
    assert df["total_charges"].iloc[0] == pytest.approx(358.20)


def test_transform_total_charges_empty_string_becomes_nan(raw_telco_df):
    """String vazia ou espaço em Total Charges resulta em NaN (coerce)."""
    raw_telco_df.loc[0, "Total Charges"] = " "
    df = transform(raw_telco_df)
    assert pd.isna(df["total_charges"].iloc[0])


def test_transform_total_charges_already_numeric_unchanged(raw_telco_df):
    """Total Charges que já é numérico não é alterado."""
    raw_telco_df["Total Charges"] = raw_telco_df["Total Charges"].astype(float)
    df = transform(raw_telco_df)
    assert df["total_charges"].iloc[1] == pytest.approx(1367.00)


# ---------------------------------------------------------------------------
# transform() — imutabilidade do input
# ---------------------------------------------------------------------------


def test_transform_does_not_mutate_input(raw_telco_df):
    """transform() não modifica o DataFrame original passado como argumento."""
    original_columns = list(raw_telco_df.columns)
    original_partner_value = raw_telco_df["Partner"].iloc[0]
    transform(raw_telco_df)
    assert list(raw_telco_df.columns) == original_columns
    assert raw_telco_df["Partner"].iloc[0] == original_partner_value


# ---------------------------------------------------------------------------
# load() — enriquecimento com IDs e envio ao banco (engine mockado)
# ---------------------------------------------------------------------------


def _capture_to_sql(raw_telco_df):
    """Executa load() com engine mock e retorna o DataFrame enviado ao to_sql."""
    df = transform(raw_telco_df)
    captured = []

    def fake_to_sql(self, name, con, **kwargs):
        captured.append(self.copy())

    with patch.object(pd.DataFrame, "to_sql", fake_to_sql):
        load(df, object(), tenant_id="tenant-uuid", project_id="project-uuid")

    return captured[0]


def test_load_injects_tenant_id(raw_telco_df):
    """load() adiciona tenant_id em todas as linhas."""
    sent_df = _capture_to_sql(raw_telco_df)
    assert "tenant_id" in sent_df.columns
    assert (sent_df["tenant_id"] == "tenant-uuid").all()


def test_load_injects_project_id(raw_telco_df):
    """load() adiciona project_id em todas as linhas."""
    sent_df = _capture_to_sql(raw_telco_df)
    assert "project_id" in sent_df.columns
    assert (sent_df["project_id"] == "project-uuid").all()


def test_load_sets_is_synthetic_false(raw_telco_df):
    """load() marca todos os registros com is_synthetic=False."""
    sent_df = _capture_to_sql(raw_telco_df)
    assert "is_synthetic" in sent_df.columns
    assert (sent_df["is_synthetic"] == False).all()


def test_load_sends_only_expected_columns(raw_telco_df):
    """load() seleciona exatamente as colunas do COLUMN_MAP + IDs de infra."""
    sent_df = _capture_to_sql(raw_telco_df)
    expected = set(COLUMN_MAP.values()) | {"tenant_id", "project_id", "is_synthetic", "split"}
    assert set(sent_df.columns) == expected


def test_load_calls_to_sql_with_correct_table_params(raw_telco_df):
    """load() chama to_sql com name='customers', schema='churn' e if_exists='append'."""
    df = transform(raw_telco_df)
    captured_kwargs = {}

    def fake_to_sql(self, name, con, schema=None, if_exists=None, **kwargs):
        captured_kwargs["name"] = name
        captured_kwargs["schema"] = schema
        captured_kwargs["if_exists"] = if_exists

    with patch.object(pd.DataFrame, "to_sql", fake_to_sql):
        load(df, object(), tenant_id="t", project_id="p")

    assert captured_kwargs["name"] == "customers"
    assert captured_kwargs["schema"] == "churn"
    assert captured_kwargs["if_exists"] == "append"


# ---------------------------------------------------------------------------
# assign_split() — partição determinística via MD5
# ---------------------------------------------------------------------------


def test_assign_split_is_deterministic():
    """assign_split retorna o mesmo resultado para o mesmo customer_id."""
    from pipeline.load_ibm_telco import assign_split

    assert assign_split("7590-VHVEG") == assign_split("7590-VHVEG")
    assert assign_split("5575-GNVDE") == assign_split("5575-GNVDE")


def test_assign_split_returns_valid_values():
    """assign_split retorna apenas 'train' ou 'holdout'."""
    from pipeline.load_ibm_telco import assign_split

    customer_ids = [f"CUST-{i:04d}" for i in range(100)]
    splits = [assign_split(cid) for cid in customer_ids]
    assert all(s in {"train", "holdout"} for s in splits)


def test_assign_split_distribution_is_roughly_30_pct():
    """assign_split distribui aproximadamente 30% para holdout em amostra grande."""
    from pipeline.load_ibm_telco import assign_split

    customer_ids = [f"CUST-{i:06d}" for i in range(1000)]
    holdout_count = sum(1 for cid in customer_ids if assign_split(cid) == "holdout")
    ratio = holdout_count / len(customer_ids)
    assert 0.22 <= ratio <= 0.38, f"Distribuição holdout fora do esperado: {ratio:.2%}"


def test_assign_split_custom_ratio():
    """assign_split respeita holdout_ratio customizado."""
    from pipeline.load_ibm_telco import assign_split

    customer_ids = [f"CUST-{i:06d}" for i in range(1000)]
    holdout_50 = sum(1 for cid in customer_ids if assign_split(cid, holdout_ratio=0.5) == "holdout")
    ratio = holdout_50 / len(customer_ids)
    assert 0.42 <= ratio <= 0.58


def test_load_includes_split_column(raw_telco_df):
    """load() inclui a coluna split no DataFrame enviado ao banco."""
    df = transform(raw_telco_df)
    sent_df = []

    def fake_to_sql(self, name, con, **kwargs):
        sent_df.append(self.copy())

    with patch.object(pd.DataFrame, "to_sql", fake_to_sql):
        load(df, object(), tenant_id="t", project_id="p")

    assert "split" in sent_df[0].columns
    assert set(sent_df[0]["split"].unique()).issubset({"train", "holdout"})
