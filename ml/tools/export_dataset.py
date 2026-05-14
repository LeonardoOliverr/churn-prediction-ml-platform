"""
Exporta o dataset tratado para CSV — útil para inspeção, auditoria e debug.

Gera três arquivos no diretório de saída:
  features_raw.csv         — Features antes de qualquer transformação (valores originais do BD)
  features_transformed.csv — Features após ColumnTransformer (scaling + OHE aplicados)
  feature_names.txt        — Nome de cada coluna do array transformado

Uso:
    python ml/tools/export_dataset.py
    python ml/tools/export_dataset.py --tenant ibm-telco --project telco-churn-2018
    python ml/tools/export_dataset.py --output-dir data/exports/
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

# Raiz do projeto no path para imports absolutos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.config.settings import TARGET
from core.logger import get_logger
from ml.data.preprocessing import build_preprocessor, load_data

logger = get_logger()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta o dataset tratado para CSV.")
    parser.add_argument("--tenant", default=None, help="Slug do tenant. Omitir para escopo global.")
    parser.add_argument("--project", default=None, help="Slug do projeto. Requer --tenant.")
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Diretório onde os CSVs serão salvos (default: data/).",
    )
    args = parser.parse_args()

    if args.project and not args.tenant:
        parser.error("--project requer --tenant.")

    return args


def _get_feature_names(preprocessor) -> list[str]:
    """Extrai os nomes das colunas após fit do ColumnTransformer."""
    if hasattr(preprocessor, "get_feature_names_out"):
        try:
            raw = preprocessor.get_feature_names_out()
            return [
                name.split("__", 1)[-1] if "__" in name else name
                for name in raw.tolist()
            ]
        except Exception:
            pass

    names: list[str] = []

    for name, transformer, cols in preprocessor.transformers_:
        if transformer == "drop":
            continue
        if transformer == "passthrough":
            names.extend(cols)
        elif hasattr(transformer, "steps"):
            last_step = transformer.steps[-1][1]
            if hasattr(last_step, "get_feature_names_out"):
                names.extend(last_step.get_feature_names_out(cols).tolist())
            else:
                names.extend(cols)
        elif hasattr(transformer, "get_feature_names_out"):
            try:
                names.extend(transformer.get_feature_names_out(cols).tolist())
            except TypeError:
                names.extend(transformer.get_feature_names_out().tolist())
        else:
            names.extend(cols)

    return names


def export(
    tenant_slug: str | None = None,
    project_slug: str | None = None,
    output_dir: str = "data",
) -> None:
    """Carrega dados, aplica transformações e exporta CSVs para `output_dir`."""
    os.makedirs(output_dir, exist_ok=True)

    logger.info("data_loading_started")
    X, y = load_data(tenant_slug=tenant_slug, project_slug=project_slug)
    logger.info("data_loaded", records=len(X), churn_rate=round(float(y.mean()), 4))

    # ---- 1. CSV bruto ----
    raw_df = X.copy()
    raw_df[TARGET] = y
    raw_path = os.path.join(output_dir, "features_raw.csv")
    raw_df.to_csv(raw_path, index=False)
    logger.info("raw_csv_exported", path=raw_path, shape=list(raw_df.shape), columns=list(raw_df.columns))

    # ---- 2. Fit do preprocessor ----
    logger.info("preprocessor_fitting_started")
    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)
    logger.info("preprocessor_fitted", shape=list(X_transformed.shape))

    # ---- 3. Nomes das colunas transformadas ----
    feature_names = _get_feature_names(preprocessor)

    names_path = os.path.join(output_dir, "feature_names.txt")
    with open(names_path, "w", encoding="utf-8") as f:
        for i, name in enumerate(feature_names):
            f.write(f"{i:3d}  {name}\n")

    numeric_count = 3
    bool_count    = 5
    ohe_count     = len(feature_names) - numeric_count - bool_count
    logger.info(
        "feature_names_exported",
        path=names_path,
        total_features=len(feature_names),
        numeric=numeric_count,
        boolean=bool_count,
        ohe=ohe_count,
    )

    # ---- 4. CSV transformado ----
    cols = feature_names if len(feature_names) == X_transformed.shape[1] \
        else [f"feat_{i}" for i in range(X_transformed.shape[1])]

    transformed_df = pd.DataFrame(X_transformed, columns=cols)
    transformed_df[TARGET] = y.values

    transformed_path = os.path.join(output_dir, "features_transformed.csv")
    transformed_df.to_csv(transformed_path, index=False)
    logger.info("transformed_csv_exported", path=transformed_path, shape=list(transformed_df.shape))

    logger.info(
        "export_complete",
        output_dir=output_dir,
        churn_rate=round(float(y.mean()), 4),
        positives=int(y.sum()),
        total=len(y),
    )


def main() -> None:
    args = _parse_args()
    export(
        tenant_slug=args.tenant,
        project_slug=args.project,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
