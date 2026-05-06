# ml/ - Pipeline de Machine Learning

Módulo de treinamento multi-tenant para previsão de churn.

Ele centraliza carregamento de dados, preprocessing, definição de modelos, avaliação, logging no MLflow e registro técnico em `churn.models`.

---

## Estrutura

```text
ml/
|-- core/                # infraestrutura genérica, sem regra de negócio
|   |-- training/
|   |   |-- train.py     # treino e holdout
|   |   |-- metrics.py   # métricas e cross-validation
|   |-- registry/
|   |   |-- mlflow.py    # logging de runs e artefatos
|   |   |-- db.py        # registro em churn.models
|   |-- model_spec.py    # contrato declarativo de modelos
|
|-- data/                # dados e preprocessing
|   |-- preprocessing.py # load_data() e build_preprocessor()
|
|-- models/              # definição dos modelos
|   |-- baseline.py      # DummyClassifier e Logistic Regression
|   |-- random_forest.py # RandomForestClassifier
|
|-- evaluation/          # avaliação, relatórios e comparação
|   |-- metrics.py
|   |-- reports.py
|   |-- comparison.py
|
|-- domain/              # regras de negócio
|   |-- risk.py          # classificação de risco de churn
|
|-- config/              # configurações isoladas
|   |-- settings.py      # MLflow URI, target, features e colunas descartadas
|
|-- tools/               # scripts utilitários
|   |-- compare_models.py
|   |-- export_dataset.py
|
|-- train.py             # entrypoint CLI
|-- README.md
```

Documentação detalhada dos modelos fica em [`docs/ml/`](../docs/ml/).

---

## Orquestração

`ml/train.py` é o entrypoint CLI e orquestrador do run de treinamento. Ele coordena parse de argumentos, escopo, carga de dados, resolução de `ModelSpec`, treino, comparação, relatório e registro.

A lógica pesada permanece nos módulos especializados:

- treino em `ml/core/training/`;
- comparação e relatórios em `ml/evaluation/`;
- persistência em `ml/core/registry/`.

Na v1, a decisão é local ao run: o maior `f1_mean` vira `approved`; os demais candidatos ficam como `trained`. Essa etapa ainda não altera `churn.project_model_config`.

---

## Escopos

Todos os modelos respeitam a hierarquia multi-tenant via flags CLI:

| Escopo | `--tenant` | `--project` | Dados usados | Experimento MLflow |
|---|---|---|---|---|
| `global` | omitido | omitido | Todos os tenants | `global/<modelo>` |
| `tenant` | informado | omitido | Clientes do tenant | `{tenant}/<modelo>` |
| `project` | informado | informado | Clientes do projeto | `{tenant}/{project}/<modelo>` |

Produção não é definida por `scope`. A fonte de verdade para serving por projeto é `churn.project_model_config`.

---

## Comandos

### Baseline

Treina `DummyClassifier` e `LogisticRegression` e aprova o melhor F1 do run.

```bash
python -m ml.train --model baseline
python -m ml.train --model baseline --dry-run
python -m ml.train --model baseline --tenant ibm-telco
python -m ml.train --model baseline --tenant ibm-telco --project telco-churn-2018
```

### Random Forest

```bash
python -m ml.train --model random_forest
python -m ml.train --model random_forest --dry-run
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018
python -m ml.train --model random_forest --n-estimators 300 --max-depth 10
```

### Avaliação

```bash
# Padrão: 5-fold CV nos dados de treino + holdout fixo de 20%
python -m ml.train --model random_forest

# Holdout customizado
python -m ml.train --model random_forest --holdout-size 0.3

# CV puro, sem holdout separado
python -m ml.train --model random_forest --holdout-size 0.0
```

### Docker

```bash
docker compose --profile tools run --rm trainer python -m ml.train --model baseline --tenant ibm-telco --project telco-churn-2018
docker compose --profile tools run --rm trainer python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018
```

### Dry run

`--dry-run` executa carregamento, treino e avaliação, mas não grava:

- não cria run no MLflow;
- não faz `INSERT` em `churn.models`;
- imprime o payload que seria registrado.

---

## Ferramentas

### Exportar dataset tratado

```bash
python ml/tools/export_dataset.py
python ml/tools/export_dataset.py --tenant ibm-telco --project telco-churn-2018
python ml/tools/export_dataset.py --output-dir data/exports/
```

Arquivos gerados:

- `features_raw.csv`
- `features_transformed.csv`
- `feature_names.txt`

### Comparar modelos no MLflow

```bash
python ml/tools/compare_models.py --tenant ibm-telco
python ml/tools/compare_models.py --tenant ibm-telco --project telco-churn-2018
python ml/tools/compare_models.py --tenant ibm-telco --project telco-churn-2018 --output charts/model_comparison.png
```

---

## Fluxo De Treino

Por padrão, o pipeline usa CV para diagnóstico e holdout fixo para métrica final:

```text
Dataset completo
  ├── 20% -> holdout fixo
  └── 80% -> 5-fold StratifiedKFold
             └── treino final nos 80%
                       └── avaliação única no holdout
```

Métricas primárias (`f1_mean`, `roc_auc_mean`, `recall_mean`, `precision_mean`) vêm do holdout quando ele está ativo.
Métricas de CV recebem prefixo `cv_` e servem para diagnosticar estabilidade.
Métricas de treino recebem prefixo `train_` e ajudam a identificar overfitting.

---

## Registro

### MLflow

Cada run registra:

- parâmetros do modelo e da avaliação;
- métricas de holdout, CV e treino;
- pipeline sklearn completo em `artifact_path="model"`;
- `feature_importances.json` quando o modelo expõe importâncias, como Random Forest.

URI padrão: `http://localhost:5000`, configurável por `MLFLOW_TRACKING_URI`.

### churn.models

Catálogo técnico dos modelos treinados.

| Situação | Status |
|---|---|
| Melhor F1 do run | `approved` |
| Demais modelos do run | `trained` |

Campos principais: `name`, `version`, `scope`, `tenant_id`, `project_id`, `mlflow_run_id`, F1, ROC-AUC, Recall, Precision e `status`.

### churn.project_model_config

Define qual modelo serve tráfego em produção.

| Campo | Uso |
|---|---|
| `role` | `champion` ou `challenger` |
| `traffic_split` | fração do tráfego enviada ao challenger |
| `threshold` | threshold aplicado na predição |
| `is_active` | indica se a configuração participa da inferência |

A API resolve modelos por cascade:

```text
champion/challenger do projeto -> champion do tenant -> churn.models scope=global
```

---

## Como Adicionar Um Modelo

1. Crie um arquivo em `ml/models/`, por exemplo `ml/models/xgboost.py`.

```python
from ml.core.model_spec import ModelSpec

SPECS = [
    ModelSpec(
        name="xgboost",
        estimator_factory=lambda **p: XGBClassifier(**p),
        default_params={"n_estimators": 300, "max_depth": 6},
        cli_overrides={"n_estimators": int, "max_depth": int},
        experiment_suffix="xgboost",
        log_feature_importances=True,
    )
]
```

2. Exporte a spec em `ml/models/__init__.py`.

```python
from ml.models.xgboost import SPECS as XGBOOST_SPECS
```

3. Registre o modelo em `ml/train.py`:

- adicionar o nome em `choices` de `--model`;
- retornar `XGBOOST_SPECS` em `_resolve_specs()`.

4. Adicione documentação em `docs/ml/`.

---

## Pré-Requisitos

1. PostgreSQL e MLflow ativos: `docker compose up -d`
2. Migrações aplicadas: `cd db && ./sqitch deploy`
3. Seed aplicado: `db/seed/001_default_tenant.sql`
4. `.env` configurado com credenciais do banco

---

## Resultados Consolidados

| Modelo | F1 (holdout) | ROC-AUC | Recall |
|---|---:|---:|---:|
| DummyClassifier | 0.2413 | 0.4828 | 24.2% |
| Logistic Regression | 0.6379 | 0.8575 | 80.7% |
| Random Forest | pendente | pendente | pendente |
