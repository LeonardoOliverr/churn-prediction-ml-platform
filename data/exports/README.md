# Export Dataset

## Resumo das features numericas

Features numericas apos `StandardScaler`:

| Estatistica | tenure_months | monthly_charges | total_charges |
|---|---:|---:|---:| 
| count | 7043.000 | 7043.000 | 7043.000 |
| mean | 0.000 | -0.000 | -0.000 |
| std | 1.000 | 1.000 | 1.000 |
| min | -1.318 | -1.546 | -0.999 |
| 25% | -0.952 | -0.973 | -0.830 |
| 50% | -0.137 | 0.186 | -0.390 |
| 75% | 0.921 | 0.834 | 0.664 |
| max | 1.614 | 1.794 | 2.827 |

## Churn rate

Churn rate: **26.5%** (`1869` positivos de `7043` registros).




| Arquivo | Descricao |
|---|---|
| `features_raw.csv` | Dataset original, legivel por humanos. |
| `features_transformed.csv` | Dataset pronto para o modelo. |
| `feature_names.txt` | Indice das colunas do array transformado. |
