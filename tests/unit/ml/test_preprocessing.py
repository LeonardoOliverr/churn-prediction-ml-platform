"""
Testes unitários para ml/preprocessing.py.

Inclui schema tests para validar a estrutura do DataFrame fake e testes
da função build_preprocessor() sem dependência de banco de dados.

Nota: load_data() requer PostgreSQL ativo — fica coberta nos testes de integração.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer

from ml.config.settings import BOOL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET
from ml.data.preprocessing import build_preprocessor

# ---------------------------------------------------------------------------
# Schema tests — validam estrutura do dataset fake
# ---------------------------------------------------------------------------


@pytest.mark.schema
def test_fake_dataset_has_all_expected_columns(fake_customers_df):
    """[SCHEMA TEST] DataFrame fake contém todas as colunas de features e o target."""
    expected = set(NUMERIC_FEATURES + BOOL_FEATURES + CATEGORICAL_FEATURES + [TARGET])
    missing = expected - set(fake_customers_df.columns)
    assert missing == set(), f"Colunas ausentes no DataFrame fake: {missing}"


@pytest.mark.schema
def test_fake_dataset_target_is_binary(fake_customers_df):
    """[SCHEMA TEST] Coluna target contém apenas valores 0 e 1."""
    unique_values = set(fake_customers_df[TARGET].unique())
    assert unique_values.issubset({0, 1}), f"Valores inesperados em '{TARGET}': {unique_values}"


@pytest.mark.schema
def test_fake_dataset_has_both_classes(fake_customers_df):
    """[SCHEMA TEST] Dataset fake contém exemplos de churn e não-churn."""
    assert 0 in fake_customers_df[TARGET].values
    assert 1 in fake_customers_df[TARGET].values


@pytest.mark.schema
def test_fake_dataset_numeric_columns_are_numeric(fake_customers_df):
    """[SCHEMA TEST] Colunas numéricas são do tipo float ou int."""
    for col in NUMERIC_FEATURES:
        assert pd.api.types.is_numeric_dtype(fake_customers_df[col]), (
            f"Coluna '{col}' deveria ser numérica."
        )


# ---------------------------------------------------------------------------
# Unit tests — validam build_preprocessor()
# ---------------------------------------------------------------------------


def test_build_preprocessor_returns_column_transformer():
    """build_preprocessor() retorna instância de ColumnTransformer."""
    preprocessor = build_preprocessor()
    assert isinstance(preprocessor, ColumnTransformer)


def test_preprocessor_has_three_transformers():
    """Pipeline tem exatamente os três transformers: numeric, bool e categorical."""
    preprocessor = build_preprocessor()
    transformer_names = [name for name, _, _ in preprocessor.transformers]
    assert "numeric" in transformer_names
    assert "bool" in transformer_names
    assert "categorical" in transformer_names


def test_preprocessor_transforms_fake_data(fake_customers_df):
    """Preprocessor transforma o DataFrame fake sem erros e retorna array 2D."""
    X = fake_customers_df.drop(columns=[TARGET])
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(X)

    assert result is not None
    assert result.ndim == 2
    assert result.shape[0] == len(fake_customers_df)
    assert result.shape[1] > 0


def test_preprocessor_output_not_empty(fake_customers_df):
    """Saída do preprocessor não está vazia."""
    X = fake_customers_df.drop(columns=[TARGET])
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(X)

    assert result.shape[0] > 0
    assert result.shape[1] > 0


def test_preprocessor_output_has_no_nan(fake_customers_df):
    """Saída do preprocessor não contém NaN — imputers devem ter atuado."""
    X = fake_customers_df.drop(columns=[TARGET])
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(X)

    assert not np.isnan(result).any(), "Preprocessor gerou NaN na saída."


def test_preprocessor_handles_nulls_in_input():
    """Preprocessor trata valores nulos na entrada sem gerar NaN na saída."""
    df_with_nulls = pd.DataFrame(
        {
            "tenure_months": [12.0, None],
            "monthly_charges": [29.85, 56.95],
            "total_charges": [358.20, None],
            "senior_citizen": [0.0, 1.0],
            "partner": [1.0, 0.0],
            "dependents": [0.0, 0.0],
            "phone_service": [0.0, 1.0],
            "paperless_billing": [1.0, 0.0],
            "gender": ["Female", np.nan],
            "multiple_lines": ["No", "Yes"],
            "internet_service": ["DSL", "Fiber optic"],
            "online_security": ["No", "No"],
            "online_backup": ["Yes", "No"],
            "device_protection": ["No", "Yes"],
            "tech_support": ["No", "No"],
            "streaming_tv": ["No", "Yes"],
            "streaming_movies": ["No", "No"],
            "contract": ["Month-to-month", "One year"],
            "payment_method": ["Electronic check", "Mailed check"],
        }
    )

    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(df_with_nulls)

    assert not np.isnan(result).any(), "Preprocessor não tratou valores nulos corretamente."


def test_preprocessor_number_of_output_columns(fake_customers_df):
    """Número de colunas de saída é maior que o número de features de entrada.

    OneHotEncoder expande colunas categóricas, então a saída sempre terá
    mais colunas que a entrada.
    """
    X = fake_customers_df.drop(columns=[TARGET])
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(X)

    n_input_features = len(NUMERIC_FEATURES) + len(BOOL_FEATURES) + len(CATEGORICAL_FEATURES)
    assert result.shape[1] > n_input_features


# ---------------------------------------------------------------------------
# load_data() — parâmetro split
# ---------------------------------------------------------------------------


def test_load_data_invalid_split_raises_value_error():
    """load_data() com split inválido levanta ValueError antes de acessar o banco."""
    from ml.data.preprocessing import load_data

    with pytest.raises(ValueError, match="split deve ser"):
        load_data(split="test")


def test_load_data_invalid_split_value_all_raises():
    """Valor 'all' não é aceito — deve ser None para carregar todos."""
    from ml.data.preprocessing import load_data

    with pytest.raises(ValueError):
        load_data(split="all")


def test_load_data_none_split_does_not_raise():
    """split=None é aceito (carrega todos os registros) sem levantar erro de validação."""
    from unittest.mock import MagicMock, patch

    import pandas as pd

    from ml.data.preprocessing import load_data

    mock_df = pd.DataFrame(columns=["churn_value"])
    with patch("ml.data.preprocessing._build_engine") as mock_engine_fn:
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.scalar_one.return_value = "uuid"
        mock_engine_fn.return_value.connect.return_value = mock_conn
        with patch("pandas.read_sql", return_value=mock_df):
            try:
                load_data(split=None)
            except Exception as e:
                assert "split deve ser" not in str(e)


def test_load_data_train_split_is_default():
    """split='train' é o default — não levanta erro de validação."""
    from unittest.mock import MagicMock, patch

    import pandas as pd

    from ml.data.preprocessing import load_data

    mock_df = pd.DataFrame(columns=["churn_value"])
    with patch("ml.data.preprocessing._build_engine") as mock_engine_fn:
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine_fn.return_value.connect.return_value = mock_conn
        with patch("pandas.read_sql", return_value=mock_df):
            try:
                load_data()
            except Exception as e:
                assert "split deve ser" not in str(e)


# ---------------------------------------------------------------------------
# _resolve_tenant_id() e _resolve_project_id()
# ---------------------------------------------------------------------------


def test_build_engine_uses_env_vars():
    """_build_engine() lê variáveis de ambiente e chama create_engine com a URL correta."""
    import os
    from unittest.mock import MagicMock, patch

    from ml.data.preprocessing import _build_engine

    env = {
        "POSTGRES_USER": "churn_user",
        "POSTGRES_PASSWORD": "churn_pass",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5434",
        "POSTGRES_DB": "churn_dev",
    }
    mock_engine = MagicMock()
    with (
        patch.dict(os.environ, env, clear=False),
        patch("ml.data.preprocessing.create_engine", return_value=mock_engine) as mock_ce,
    ):
        engine = _build_engine()

    assert engine is mock_engine
    url = mock_ce.call_args[0][0]
    assert "churn_user" in url
    assert "churn_pass" in url
    assert "churn_dev" in url
    assert "5434" in url


def test_resolve_tenant_id_with_slug_queries_by_slug():
    """Com tenant_slug fornecido, executa query com parâmetro :s."""
    from unittest.mock import MagicMock

    from ml.data.preprocessing import _resolve_tenant_id

    conn = MagicMock()
    conn.execute.return_value.scalar_one.return_value = "tenant-uuid"

    result = _resolve_tenant_id(conn, "ibm-telco")

    assert result == "tenant-uuid"
    call_params = conn.execute.call_args[0][1]
    assert call_params["s"] == "ibm-telco"


def test_resolve_tenant_id_without_slug_queries_first_tenant():
    """Com tenant_slug=None, executa query sem filtro (LIMIT 1)."""
    from unittest.mock import MagicMock

    from ml.data.preprocessing import _resolve_tenant_id

    conn = MagicMock()
    conn.execute.return_value.scalar_one.return_value = "any-uuid"

    result = _resolve_tenant_id(conn, None)

    assert result == "any-uuid"
    # chamada sem parâmetros extras (só o text SQL)
    assert len(conn.execute.call_args[0]) == 1


def test_resolve_project_id_queries_by_tenant_and_slug():
    """_resolve_project_id passa tenant_id e slug na query."""
    from unittest.mock import MagicMock

    from ml.data.preprocessing import _resolve_project_id

    conn = MagicMock()
    conn.execute.return_value.scalar_one.return_value = "project-uuid"

    result = _resolve_project_id(conn, "tenant-uuid", "telco-churn-2018")

    assert result == "project-uuid"
    call_params = conn.execute.call_args[0][1]
    assert call_params["t"] == "tenant-uuid"
    assert call_params["s"] == "telco-churn-2018"


# ---------------------------------------------------------------------------
# load_data() — branches com tenant_slug e project_slug
# ---------------------------------------------------------------------------


def _mock_load_engine(fake_df):
    """Cria engine + conn mock prontos para load_data()."""
    from unittest.mock import MagicMock

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.scalar_one.return_value = "some-uuid"
    return mock_conn


def test_load_data_with_tenant_slug_only(fake_customers_df):
    """tenant_slug sem project_slug usa branch intermediário (elif)."""
    from unittest.mock import patch

    from ml.data.preprocessing import load_data

    mock_conn = _mock_load_engine(fake_customers_df)
    with (
        patch("ml.data.preprocessing._build_engine") as mock_engine_fn,
        patch("pandas.read_sql", return_value=fake_customers_df),
    ):
        mock_engine_fn.return_value.connect.return_value = mock_conn
        X, y = load_data(tenant_slug="ibm-telco", project_slug=None, split="train")

    assert X is not None
    assert len(y) > 0


def test_load_data_with_tenant_and_project_slug(fake_customers_df):
    """tenant_slug + project_slug usa branch completo (else)."""
    from unittest.mock import patch

    from ml.data.preprocessing import load_data

    mock_conn = _mock_load_engine(fake_customers_df)
    with (
        patch("ml.data.preprocessing._build_engine") as mock_engine_fn,
        patch("pandas.read_sql", return_value=fake_customers_df),
    ):
        mock_engine_fn.return_value.connect.return_value = mock_conn
        X, y = load_data(tenant_slug="ibm-telco", project_slug="telco-churn-2018", split="train")

    assert X is not None
    assert len(y) > 0


def test_load_data_with_tenant_slug_and_none_split(fake_customers_df):
    """split=None com tenant_slug não filtra por split na query."""
    from unittest.mock import patch

    from ml.data.preprocessing import load_data

    mock_conn = _mock_load_engine(fake_customers_df)
    with (
        patch("ml.data.preprocessing._build_engine") as mock_engine_fn,
        patch("pandas.read_sql", return_value=fake_customers_df),
    ):
        mock_engine_fn.return_value.connect.return_value = mock_conn
        X, y = load_data(tenant_slug="ibm-telco", project_slug=None, split=None)

    assert X is not None


def test_load_data_with_project_and_none_split(fake_customers_df):
    """split=None com tenant+project não filtra por split na query."""
    from unittest.mock import patch

    from ml.data.preprocessing import load_data

    mock_conn = _mock_load_engine(fake_customers_df)
    with (
        patch("ml.data.preprocessing._build_engine") as mock_engine_fn,
        patch("pandas.read_sql", return_value=fake_customers_df),
    ):
        mock_engine_fn.return_value.connect.return_value = mock_conn
        X, y = load_data(tenant_slug="ibm-telco", project_slug="telco-churn-2018", split=None)

    assert X is not None
