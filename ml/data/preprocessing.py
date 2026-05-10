"""PostgreSQL data loading and reusable sklearn preprocessing."""

import os

import pandas as pd
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import create_engine, text

from ml.config.settings import (
    BOOL_FEATURES,
    CATEGORICAL_FEATURES,
    DROP_COLS,
    NUMERIC_FEATURES,
    TARGET,
)

load_dotenv()


def _build_engine():
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


def _resolve_tenant_id(conn, tenant_slug: str | None) -> str:
    if tenant_slug is None:
        return str(
            conn.execute(text("SELECT id FROM churn.tenants LIMIT 1")).scalar_one()
        )
    return str(
        conn.execute(
            text("SELECT id FROM churn.tenants WHERE slug = :s"),
            {"s": tenant_slug},
        ).scalar_one()
    )


def _resolve_project_id(conn, tenant_id: str, project_slug: str) -> str:
    return str(
        conn.execute(
            text("SELECT id FROM churn.projects WHERE tenant_id = :t AND slug = :s"),
            {"t": tenant_id, "s": project_slug},
        ).scalar_one()
    )


def load_data(
    tenant_slug: str | None = None,
    project_slug: str | None = None,
    split: str | None = "train",
) -> tuple[pd.DataFrame, pd.Series]:
    """Load churn.customers from PostgreSQL and return sklearn-ready (X, y).

    Parâmetro split filtra por partição: 'train', 'holdout' ou None (todos).
    Default 'train' garante compatibilidade com callers existentes.
    """
    if split not in ("train", "holdout", None):
        raise ValueError(f"split deve ser 'train', 'holdout' ou None, recebido: {split!r}")

    engine = _build_engine()

    with engine.connect() as conn:
        if tenant_slug is None:
            query = "SELECT * FROM churn.customers"
            params: dict = {}
            if split is not None:
                query += " WHERE split = :split"
                params["split"] = split
            df = pd.read_sql(text(query), conn, params=params or None)

        elif project_slug is None:
            tenant_id = _resolve_tenant_id(conn, tenant_slug)
            query = "SELECT * FROM churn.customers WHERE tenant_id = :t"
            params = {"t": tenant_id}
            if split is not None:
                query += " AND split = :split"
                params["split"] = split
            df = pd.read_sql(text(query), conn, params=params)

        else:
            tenant_id = _resolve_tenant_id(conn, tenant_slug)
            project_id = _resolve_project_id(conn, tenant_id, project_slug)
            query = "SELECT * FROM churn.customers WHERE tenant_id = :t AND project_id = :p"
            params = {"t": tenant_id, "p": project_id}
            if split is not None:
                query += " AND split = :split"
                params["split"] = split
            df = pd.read_sql(text(query), conn, params=params)

    df = df.drop(columns=DROP_COLS, errors="ignore")

    for col in BOOL_FEATURES:
        df[col] = pd.to_numeric(
            df[col].map({True: 1, False: 0, 1: 1, 0: 0}),
            errors="coerce",
        )

    y = df[TARGET].astype(int)
    X = df.drop(columns=[TARGET])
    return X, y


def build_preprocessor() -> ColumnTransformer:
    """Return the configured imputation, scaling, and encoding transformer."""
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("bool", "passthrough", BOOL_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
