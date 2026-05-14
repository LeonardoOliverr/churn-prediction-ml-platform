"""
Testes unitários para ml/tools/export_dataset.py.

Cobre _parse_args, _get_feature_names (todos os branches) e export()
sem banco de dados real, usando fake_customers_df e tmp_path.
"""

import sys
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    """Sem argumentos, retorna tenant=None, project=None, output_dir='data'."""
    from ml.tools.export_dataset import _parse_args
    with patch.object(sys, "argv", ["export_dataset.py"]):
        args = _parse_args()
    assert args.tenant is None
    assert args.project is None
    assert args.output_dir == "data"


def test_parse_args_com_tenant_e_project():
    from ml.tools.export_dataset import _parse_args
    with patch.object(sys, "argv", [
        "export_dataset.py", "--tenant", "ibm-telco",
        "--project", "telco-churn-2018",
        "--output-dir", "exports/",
    ]):
        args = _parse_args()
    assert args.tenant == "ibm-telco"
    assert args.project == "telco-churn-2018"
    assert args.output_dir == "exports/"


def test_parse_args_project_sem_tenant_sai_com_erro():
    """--project sem --tenant deve levantar SystemExit."""
    from ml.tools.export_dataset import _parse_args
    with patch.object(sys, "argv", ["export_dataset.py", "--project", "my-project"]), \
         pytest.raises(SystemExit):
        _parse_args()


# ---------------------------------------------------------------------------
# _get_feature_names — branch com preprocessor real fitado
# ---------------------------------------------------------------------------


def test_get_feature_names_retorna_lista_de_strings(fake_customers_df):
    """Preprocessor real fitado retorna lista de nomes sem prefixo de transformer."""
    from ml.tools.export_dataset import _get_feature_names
    from ml.data.preprocessing import build_preprocessor
    from ml.config.settings import TARGET

    X = fake_customers_df.drop(columns=[TARGET])
    preprocessor = build_preprocessor()
    preprocessor.fit(X)

    names = _get_feature_names(preprocessor)
    assert isinstance(names, list)
    assert len(names) > 0
    assert all(isinstance(n, str) for n in names)


def test_get_feature_names_remove_prefixo_do_transformer(fake_customers_df):
    """Nenhum nome deve conter prefixo 'numeric__', 'bool__' ou 'categorical__'."""
    from ml.tools.export_dataset import _get_feature_names
    from ml.data.preprocessing import build_preprocessor
    from ml.config.settings import TARGET

    X = fake_customers_df.drop(columns=[TARGET])
    preprocessor = build_preprocessor()
    preprocessor.fit(X)

    names = _get_feature_names(preprocessor)
    prefixes = ("numeric__", "bool__", "categorical__")
    assert not any(n.startswith(p) for n in names for p in prefixes)


def test_get_feature_names_cai_para_loop_quando_get_feature_names_out_falha():
    """Se get_feature_names_out() levanta Exception, executa loop manual."""
    from ml.tools.export_dataset import _get_feature_names

    mock_preprocessor = MagicMock()
    mock_preprocessor.get_feature_names_out.side_effect = ValueError("not fitted")
    mock_preprocessor.transformers_ = [
        ("step", "passthrough", ["col_a", "col_b"]),
    ]

    names = _get_feature_names(mock_preprocessor)
    assert names == ["col_a", "col_b"]


# ---------------------------------------------------------------------------
# _get_feature_names — branches do loop manual
# ---------------------------------------------------------------------------


def test_get_feature_names_branch_passthrough():
    """transformer == 'passthrough' estende nomes diretamente com as colunas."""
    from ml.tools.export_dataset import _get_feature_names

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [
        ("step", "passthrough", ["col_a", "col_b"]),
    ]

    names = _get_feature_names(mock_preprocessor)
    assert names == ["col_a", "col_b"]


def test_get_feature_names_branch_drop():
    """transformer == 'drop' não adiciona nenhum nome."""
    from ml.tools.export_dataset import _get_feature_names

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [
        ("step", "drop", ["ignored_col"]),
    ]

    names = _get_feature_names(mock_preprocessor)
    assert names == []


def test_get_feature_names_branch_pipeline_com_get_feature_names_out():
    """Transformer com 'steps' usa o último step para extrair nomes."""
    from ml.tools.export_dataset import _get_feature_names

    mock_last = MagicMock()
    mock_last.get_feature_names_out.return_value = np.array(["feat_a", "feat_b"])

    mock_pipeline = MagicMock()
    mock_pipeline.steps = [("enc", MagicMock()), ("last", mock_last)]

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [("pipe_step", mock_pipeline, ["raw"])]

    names = _get_feature_names(mock_preprocessor)
    assert names == ["feat_a", "feat_b"]


def test_get_feature_names_branch_pipeline_sem_get_feature_names_out():
    """Último step do pipeline sem get_feature_names_out usa as colunas originais."""
    from ml.tools.export_dataset import _get_feature_names

    class _LastStep:
        pass

    mock_pipeline = MagicMock()
    mock_pipeline.steps = [("last", _LastStep())]

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [("pipe_step", mock_pipeline, ["col_x"])]

    names = _get_feature_names(mock_preprocessor)
    assert names == ["col_x"]


def test_get_feature_names_branch_transformer_com_get_feature_names_out():
    """Transformer simples com get_feature_names_out chama com colunas."""
    from ml.tools.export_dataset import _get_feature_names

    mock_transformer = MagicMock(spec=["get_feature_names_out"])
    mock_transformer.get_feature_names_out.return_value = np.array(["ohe_a", "ohe_b"])

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [("ohe", mock_transformer, ["cat_col"])]

    names = _get_feature_names(mock_preprocessor)
    assert "ohe_a" in names
    assert "ohe_b" in names


def test_get_feature_names_branch_transformer_get_feature_names_out_type_error():
    """TypeError na chamada com cols faz fallback para chamada sem args."""
    from ml.tools.export_dataset import _get_feature_names

    mock_transformer = MagicMock(spec=["get_feature_names_out"])
    mock_transformer.get_feature_names_out.side_effect = [
        TypeError("unexpected keyword"),
        np.array(["feat_no_cols"]),
    ]

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [("step", mock_transformer, ["col"])]

    names = _get_feature_names(mock_preprocessor)
    assert names == ["feat_no_cols"]


def test_get_feature_names_branch_else_sem_metodos():
    """Transformer sem steps nem get_feature_names_out usa colunas originais."""
    from ml.tools.export_dataset import _get_feature_names

    class _SimpleTransformer:
        pass

    mock_preprocessor = MagicMock(spec=["transformers_"])
    mock_preprocessor.transformers_ = [("step", _SimpleTransformer(), ["col_x", "col_y"])]

    names = _get_feature_names(mock_preprocessor)
    assert names == ["col_x", "col_y"]


# ---------------------------------------------------------------------------
# export()
# ---------------------------------------------------------------------------


def test_export_cria_tres_arquivos(fake_customers_df, tmp_path):
    """export() deve gerar features_raw.csv, features_transformed.csv e feature_names.txt."""
    from ml.tools.export_dataset import export
    from ml.config.settings import TARGET

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.tools.export_dataset.load_data", return_value=(X, y)):
        export(output_dir=str(tmp_path))

    assert (tmp_path / "features_raw.csv").exists()
    assert (tmp_path / "features_transformed.csv").exists()
    assert (tmp_path / "feature_names.txt").exists()


def test_export_raw_csv_tem_coluna_target(fake_customers_df, tmp_path):
    from ml.tools.export_dataset import export
    from ml.config.settings import TARGET

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.tools.export_dataset.load_data", return_value=(X, y)):
        export(output_dir=str(tmp_path))

    raw_df = pd.read_csv(tmp_path / "features_raw.csv")
    assert TARGET in raw_df.columns


def test_export_transformed_csv_tem_mesma_quantidade_de_linhas(fake_customers_df, tmp_path):
    from ml.tools.export_dataset import export
    from ml.config.settings import TARGET

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.tools.export_dataset.load_data", return_value=(X, y)):
        export(output_dir=str(tmp_path))

    transformed_df = pd.read_csv(tmp_path / "features_transformed.csv")
    assert len(transformed_df) == len(fake_customers_df)


def test_export_feature_names_txt_nao_vazio(fake_customers_df, tmp_path):
    from ml.tools.export_dataset import export
    from ml.config.settings import TARGET

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    with patch("ml.tools.export_dataset.load_data", return_value=(X, y)):
        export(output_dir=str(tmp_path))

    content = (tmp_path / "feature_names.txt").read_text()
    assert len(content.strip()) > 0


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_chama_export_com_args_corretos():
    from ml.tools.export_dataset import main
    with patch.object(sys, "argv", [
        "export_dataset.py", "--tenant", "ibm-telco", "--output-dir", "out/",
    ]), patch("ml.tools.export_dataset.export") as mock_export:
        main()

    mock_export.assert_called_once_with(
        tenant_slug="ibm-telco",
        project_slug=None,
        output_dir="out/",
    )
