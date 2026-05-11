"""
Baixa o dataset IBM Telco via kagglehub e faz bulk insert em churn.customers.
Pré-requisito: sqitch deploy + psql -f db/seed/001_default_tenant.sql
"""

import hashlib
import os

import kagglehub
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from core.logger import get_logger

load_dotenv()

logger = get_logger()

TENANT_SLUG = "ibm-telco"
PROJECT_SLUG = "telco-churn-2018"

YES_NO_COLS = [
    "Senior Citizen",
    "Partner",
    "Dependents",
    "Phone Service",
    "Paperless Billing",
]

COLUMN_MAP = {
    "CustomerID":       "customer_id",
    "Count":            "customer_count",
    "Country":          "country",
    "State":            "state",
    "City":             "city",
    "Zip Code":         "zip_code",
    "Lat Long":         "lat_long",
    "Latitude":         "latitude",
    "Longitude":        "longitude",
    "Gender":           "gender",
    "Senior Citizen":   "senior_citizen",
    "Partner":          "partner",
    "Dependents":       "dependents",
    "Tenure Months":    "tenure_months",
    "Phone Service":    "phone_service",
    "Multiple Lines":   "multiple_lines",
    "Internet Service": "internet_service",
    "Online Security":  "online_security",
    "Online Backup":    "online_backup",
    "Device Protection":"device_protection",
    "Tech Support":     "tech_support",
    "Streaming TV":     "streaming_tv",
    "Streaming Movies": "streaming_movies",
    "Contract":         "contract",
    "Paperless Billing":"paperless_billing",
    "Payment Method":   "payment_method",
    "Monthly Charges":  "monthly_charges",
    "Total Charges":    "total_charges",
    "Churn Label":      "churn_label",
    "Churn Value":      "churn_value",
    "Churn Score":      "churn_score",
    "CLTV":             "cltv",
    "Churn Reason":     "churn_reason",
}


def assign_split(customer_id: str, holdout_ratio: float = 0.3) -> str:
    """Atribui 'train' ou 'holdout' deterministicamente via MD5.

    Equivalente à expressão SQL na migration 14_holdout_evaluation:
        (('x' || md5(customer_id))::bit(32)::bigint + 2147483648)::numeric / 4294967296.0 < 0.3
    """
    digest = hashlib.md5(customer_id.encode()).hexdigest()
    val = int(digest[:8], 16)       # uint32: [0, 2^32-1]
    bucket = val / 4294967296.0     # [0.0, 1.0)
    return "holdout" if bucket < holdout_ratio else "train"


def build_engine():
    user     = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host     = os.environ.get("POSTGRES_HOST", "localhost")
    port     = os.environ.get("POSTGRES_PORT", "5432")
    db       = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


def fetch_dataset() -> pd.DataFrame:
    logger.info("baixando dataset", source="kagglehub")
    path = kagglehub.dataset_download("yeanzc/telco-customer-churn-ibm-dataset")
    xlsx = os.path.join(path, "Telco_customer_churn.xlsx")
    df = pd.read_excel(xlsx)
    logger.info("dataset carregado", records=len(df))
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Yes/No → bool
    for col in YES_NO_COLS:
        df[col] = df[col].str.strip().str.lower().map({"yes": True, "no": False})

    # Zip Code como string (evita tratar como int)
    df["Zip Code"] = df["Zip Code"].astype(str)

    # Total Charges: coerce strings vazias para NaN
    df["Total Charges"] = pd.to_numeric(df["Total Charges"], errors="coerce")

    return df.rename(columns=COLUMN_MAP)


def resolve_ids(engine, tenant_slug: str, project_slug: str) -> tuple[str, str]:
    with engine.connect() as conn:
        tenant_id = str(conn.execute(
            text("SELECT id FROM churn.tenants WHERE slug = :s"),
            {"s": tenant_slug},
        ).scalar_one())
        project_id = str(conn.execute(
            text("SELECT id FROM churn.projects WHERE tenant_id = :t AND slug = :s"),
            {"t": tenant_id, "s": project_slug},
        ).scalar_one())
    return tenant_id, project_id


def load(df: pd.DataFrame, engine, tenant_id: str, project_id: str):
    df = df.copy()
    df["tenant_id"] = tenant_id
    df["project_id"] = project_id
    df["is_synthetic"] = False
    df["split"] = df["customer_id"].apply(assign_split)

    db_cols = list(COLUMN_MAP.values()) + ["tenant_id", "project_id", "is_synthetic", "split"]
    df = df[db_cols]

    logger.info("inserindo registros", table="churn.customers", count=len(df))
    df.to_sql(
        name="customers",
        schema="churn",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=500,
        method="multi",
    )
    logger.info("carga concluída", table="churn.customers")


def main():
    engine = build_engine()
    df_raw = fetch_dataset()
    df = transform(df_raw)
    tenant_id, project_id = resolve_ids(engine, TENANT_SLUG, PROJECT_SLUG)
    load(df, engine, tenant_id, project_id)


if __name__ == "__main__":
    main()
