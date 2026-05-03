# ml/ — Pipeline de Machine Learning

Módulo de treinamento multi-tenant para previsão de churn.
Suporta múltiplos modelos, três escopos de dados, dry-run e registro automático no MLflow e em `churn.models`.

---

## Estrutura

```
ml/
  core/              — biblioteca compartilhada (importada por models, tools e API)
    config.py        — constantes globais: MLflow URI, feature groups, colunas descartadas
    preprocessing.py — load_data() + build_preprocessor()
    risk.py          — classify_risk() — compartilhado com a API de inferência
    __init__.py

  models/            — um arquivo por modelo, todos com a mesma interface CLI
    baseline.py      — DummyClassifier + Logistic Regression
    random_forest.py — (pendente)
    boosting.py      — (pendente)
    baseline_fe.py   — (pendente)
    mlp.py           — (pendente — será implementado após árvores)
    __init__.py
    MODELS.md        — guia completo de cada modelo: o que é, quando usar, limitações
    BASELINE.md      — resultados numéricos do experimento baseline

  tools/             — scripts utilitários, não são modelos
    export_dataset.py — exporta o dataset tratado para CSV (inspeção e auditoria)
    __init__.py
```

---

## Escopos de treinamento

Todos os modelos respeitam a hierarquia multi-tenant via flags CLI:

| Escopo | `--tenant` | `--project` | Dados usados | Experimento MLflow |
|---|---|---|---|---|
| `global` | — | — | Todos os tenants | `global/<modelo>` |
| `tenant` | ✓ | — | Só esse tenant | `{tenant}/<modelo>` |
| `project` | ✓ | ✓ | Só esse projeto | `{tenant}/{project}/<modelo>` |

> Produção não é definida por `scope` — é definida por `churn.project_model_config`.

---

## Comandos

### Baseline (DummyClassifier + Logistic Regression)

```bash
python ml/models/baseline.py
python ml/models/baseline.py --dry-run
python ml/models/baseline.py --tenant ibm-telco --project telco-churn-2018
python ml/models/baseline.py --tenant ibm-telco --project telco-churn-2018 --dry-run
```

### Random Forest

```bash
python ml/models/random_forest.py
python ml/models/random_forest.py --dry-run
python ml/models/random_forest.py --tenant ibm-telco --project telco-churn-2018
```

### Exportar dataset tratado para CSV

```bash
python ml/tools/export_dataset.py
python ml/tools/export_dataset.py --tenant ibm-telco --project telco-churn-2018
python ml/tools/export_dataset.py --output-dir data/exports/
# Gera: data/features_raw.csv, data/features_transformed.csv, data/feature_names.txt
```

### Via Docker (ambiente isolado com MLflow interno)

```bash
docker compose --profile tools run --rm trainer python ml/models/baseline.py --tenant ibm-telco --project telco-churn-2018
docker compose --profile tools run --rm trainer python ml/models/random_forest.py --tenant ibm-telco --project telco-churn-2018
```

### Flag `--dry-run`

Disponível em todos os modelos. Executa treino e CV completos, mas **não grava nada**:
- Sem runs no MLflow
- Sem INSERT em `churn.models`
- Imprime o payload exato que seria gravado

---

## Pré-requisitos

1. `docker compose up -d` — PostgreSQL e MLflow rodando
2. `cd db && ./sqitch deploy` — migrações aplicadas
3. Seed aplicado (`db/seed/001_default_tenant.sql`)
4. `.env` configurado com credenciais do banco

---

## O que é registrado após o treino

### MLflow

| O que | Detalhe |
|---|---|
| Parâmetros | tipo do modelo, folds, estratégia de CV, hiperparâmetros |
| Métricas | F1, ROC-AUC, Recall, Precision — média ± desvio dos 5 folds |
| Artefato | pipeline completo serializado em `artifact_path="model"` |

Acesse em: `http://localhost:5000`

### churn.models

Catálogo técnico de todos os modelos treinados:

| Situação | Status |
|---|---|
| Melhor F1 do run | `approved` — elegível para produção |
| Demais modelos do run | `trained` — registrado, não elegível |

Campos registrados: `name`, `version` (v1, v2…), `scope`, `tenant_id`, `project_id`, `mlflow_run_id`, F1, ROC-AUC, Recall, Precision.

### churn.project_model_config

Fonte de verdade da produção por projeto. A API resolve com cascade:
```
project_model_config do projeto → project_model_config do tenant → churn.models scope=global
```

---

## Como adicionar um novo modelo

1. Criar `ml/models/<nome>.py` seguindo a estrutura de `baseline.py`:
   - Importar `load_data` e `build_preprocessor` de `ml.core.preprocessing`
   - Implementar `_derive_scope()`, `_cv_metrics()`, `_register_in_db()`, `main()`
   - Suportar `--tenant`, `--project`, `--dry-run`
   - Logar métricas no MLflow e registrar em `churn.models`

2. Adicionar linha na tabela de `MODEL_COMPARISON.md`

3. Adicionar seção em `MODELS.md` com descrição do modelo

---

## Resultados consolidados

Ver [MODEL_COMPARISON.md](../MODEL_COMPARISON.md) e [models/MODELS.md](models/MODELS.md) para comparação e guia completo.

| Modelo | F1 | ROC-AUC | Recall |
|---|---|---|---|
| DummyClassifier | 0.2413 | 0.4828 | 24.2% |
| **Logistic Regression** | **0.6379** | **0.8575** | **80.7%** |
| Random Forest | — | — | — |
| XGBoost / LightGBM | — | — | — |
| LogReg + Feature Engineering | — | — | — |
| MLP | — | — | — |
