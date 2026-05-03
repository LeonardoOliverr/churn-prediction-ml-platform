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

from ml.core.config import TARGET
from ml.core.preprocessing import build_preprocessor, load_data


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
    names: list[str] = []

    for name, transformer, cols in preprocessor.transformers_:
        if transformer == "passthrough":
            names.extend(cols)
        else:
            last_step = transformer.steps[-1][1]
            if hasattr(last_step, "get_feature_names_out"):
                names.extend(last_step.get_feature_names_out(cols).tolist())
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

    print(f"Carregando dados do PostgreSQL...")
    X, y = load_data(tenant_slug=tenant_slug, project_slug=project_slug)
    print(f"  {len(X)} registros | churn rate: {y.mean():.1%}")

    # ---- 1. CSV bruto ----
    raw_df = X.copy()
    raw_df[TARGET] = y
    raw_path = os.path.join(output_dir, "features_raw.csv")
    raw_df.to_csv(raw_path, index=False)
    print(f"\n[1/3] features_raw.csv exportado → {raw_path}")
    print(f"      Shape: {raw_df.shape} | Colunas: {list(raw_df.columns)}")

    # ---- 2. Fit do preprocessor ----
    print(f"\nAplicando ColumnTransformer (imputation + scaling + OHE)...")
    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)
    print(f"  Shape após transformação: {X_transformed.shape}")

    # ---- 3. Nomes das colunas transformadas ----
    feature_names = _get_feature_names(preprocessor)

    names_path = os.path.join(output_dir, "feature_names.txt")
    with open(names_path, "w", encoding="utf-8") as f:
        for i, name in enumerate(feature_names):
            f.write(f"{i:3d}  {name}\n")
    print(f"\n[2/3] feature_names.txt exportado → {names_path}")
    print(f"      {len(feature_names)} features no total")

    numeric_count = 3
    bool_count    = 5
    ohe_count     = len(feature_names) - numeric_count - bool_count
    print(f"      Distribuição: {numeric_count} numéricas (scaled) | "
          f"{bool_count} booleans | {ohe_count} OHE (categorical)")

    # ---- 4. CSV transformado ----
    cols = feature_names if len(feature_names) == X_transformed.shape[1] \
        else [f"feat_{i}" for i in range(X_transformed.shape[1])]

    transformed_df = pd.DataFrame(X_transformed, columns=cols)
    transformed_df[TARGET] = y.values

    transformed_path = os.path.join(output_dir, "features_transformed.csv")
    transformed_df.to_csv(transformed_path, index=False)
    print(f"\n[3/3] features_transformed.csv exportado → {transformed_path}")
    print(f"      Shape: {transformed_df.shape}")

    print(f"\n{'='*60}")
    print("Resumo das features numéricas (após StandardScaler):")
    print(transformed_df.iloc[:, :numeric_count].describe().round(3).to_string())
    print(f"\nChurn rate: {y.mean():.1%} ({y.sum()} positivos de {len(y)})")
    print(f"{'='*60}")
    print(f"\nArquivos gerados em '{output_dir}/':")
    print(f"  • features_raw.csv          — dataset original (legível por humanos)")
    print(f"  • features_transformed.csv  — dataset pronto para o modelo")
    print(f"  • feature_names.txt         — índice das colunas do array transformado")


def main() -> None:
    args = _parse_args()
    export(
        tenant_slug=args.tenant,
        project_slug=args.project,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
