# ml/ - Pipeline de Machine Learning

Módulo de treinamento multi-tenant para previsão de churn.

Ele centraliza carregamento de dados, preprocessing, definição de modelos, avaliação, logging no MLflow e registro técnico em `churn.models`.

---

## Estrutura

```text
ml/
|-- core/                      # infraestrutura genérica
|   |-- logger.py              # logging estruturado com structlog
|   |-- model_spec.py          # contrato declarativo de ModelSpec
|
|-- config/
|   |-- settings.py            # features, DROP_COLS, MLflow URI
|
|-- data/
|   |-- preprocessing.py       # load_data() + build_preprocessor()
|
|-- models/                    # definição dos modelos
|   |-- baseline/
|   |   |-- baseline.py        # DummyClassifier + Logistic Regression
|   |-- random_forest/
|       |-- random_forest.py   # RandomForestClassifier
|
|-- evaluate_production.py     # avaliação predictions × outcomes → evaluation_run_results
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

Todos os modelos saem do run com status `candidate` — a aprovação é feita manualmente via `PATCH /admin/tenants/{t}/projects/{p}/models/{m}/approve`. Essa etapa não altera `churn.project_model_config`.

---

## Comandos

`--tenant` e `--project` são obrigatórios em todos os comandos de treino.

### Baseline

Treina `DummyClassifier` e `LogisticRegression`.

```bash
python -m ml.train --model baseline --tenant ibm-telco --project telco-churn-2018
python -m ml.train --model baseline --tenant ibm-telco --project telco-churn-2018 --dry-run
```

### Random Forest

```bash
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018 --dry-run
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018 --n-estimators 300 --max-depth 10
```

### XGBoost

```bash
python -m ml.train --model xgboost --tenant ibm-telco --project telco-churn-2018
python -m ml.train --model xgboost --tenant ibm-telco --project telco-churn-2018 --dry-run
python -m ml.train --model xgboost --tenant ibm-telco --project telco-churn-2018 --n-estimators 300 --max-depth 6
```

### Avaliação

```bash
# Padrão: 5-fold CV nos dados de treino + holdout fixo de 20%
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018

# Holdout customizado
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018 --holdout-size 0.3

# CV puro, sem holdout separado
python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018 --holdout-size 0.0
```

### Docker

```bash
docker compose --profile tools run --rm trainer python -m ml.train --model baseline --tenant ibm-telco --project telco-churn-2018
docker compose --profile tools run --rm trainer python -m ml.train --model random_forest --tenant ibm-telco --project telco-churn-2018
docker compose --profile tools run --rm trainer python -m ml.train --model xgboost --tenant ibm-telco --project telco-churn-2018
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
| Todos os modelos do run | `candidate` |

Ciclo de vida completo: `candidate` → `approved` → `retired` (ou `rejected`).
Transições registradas em `churn.model_audit_log` com `changed_by` e timestamp.

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

## Avaliação em Produção

`ml/evaluate_production.py` avalia predictions contra outcomes reais (ground truth do holdout).

```bash
# Com isolamento por ciclo (recomendado):
python -m ml.evaluate_production \
  --project telco-churn-2018 \
  --batch-id <uuid-do-ciclo> \
  --fp-cost 100 \
  --fn-cost 2000

# Por janela temporal (compatibilidade):
python -m ml.evaluate_production \
  --project telco-churn-2018 \
  --since 90d \
  --fp-cost 100 \
  --fn-cost 2000
```

Grava em `churn.evaluation_run_results`: F1, ROC-AUC, FPR/FNR, segmentação por risco e recomendação de promoção. Ver `scripts/` para scripts de suporte (seed de outcomes, predições em lote, otimização de threshold).

---

## Seleção de Threshold

O threshold define o ponto de corte da probabilidade predita a partir do qual o cliente é classificado como churn. Não existe valor universalmente correto — a escolha depende do custo operacional da intervenção de retenção.

### Trade-off recall × precision

| Threshold | Recall | Precision | Perfil de uso |
|---|---|---|---|
| 0.30–0.40 | ~0.93 | ~0.46 | Intervenção barata (e-mail, notificação) — maximizar cobertura |
| 0.45–0.55 | ~0.87 | ~0.52 | Equilíbrio — ponto de partida recomendado em produção |
| 0.60+ | ~0.80 | ~0.57 | Intervenção cara (desconto, contato humano) — alta seletividade |

Valores de referência medidos no dataset IBM Telco com XGBoost v1 (threshold_f1=0.60).

### Relação com custo de negócio

- **FN (falso negativo):** churner não identificado → perda do CLTV do cliente. Custo alto.
- **FP (falso positivo):** alarme falso → custo da intervenção desnecessária. Custo baixo se a ação for automatizada.

Quando `fn_cost >> fp_cost`, thresholds baixos minimizam custo total mas geram volume operacional alto. O ponto ótimo por custo raramente é o mesmo que o ótimo por F1 — use `scripts/optimize_threshold.py` para encontrar o equilíbrio do seu projeto.

### Como ajustar

```bash
# 1. Encontrar threshold ótimo para o ciclo atual
python scripts/optimize_threshold.py \
  --project telco-churn-2018 \
  --batch-id <uuid> \
  --fn-cost 2000 \
  --fp-cost 100

# 2. Atualizar no project_model_config via API
PATCH /admin/tenants/{t}/projects/{p}/models/{m}/champion
body: { "threshold": 0.55 }
```

---

## Resultados Consolidados

| Modelo | F1 | ROC-AUC | Recall | Precision |
|---|---:|---:|---:|---:|
| DummyClassifier | 0.3148 | 0.5347 | 30.9% | 32.0% |
| Logistic Regression | 0.6586 | 0.8636 | 82.3% | 54.9% |
| Random Forest | 0.6476 | 0.8530 | 76.7% | 56.1% |
| XGBoost (threshold=0.60) | **0.6667** | **0.8654** | **80.4%** | **56.9%** |
