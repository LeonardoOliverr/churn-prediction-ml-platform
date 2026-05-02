# ml/ - Pipeline de Treinamento

Módulo de treinamento multi-tenant. Suporta três escopos de modelo, dry-run e registro automático no catálogo técnico `churn.models`.

---

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `config.py` | Constantes globais: MLflow URI, feature lists, colunas descartadas |
| `preprocessing.py` | Carregamento de dados com filtro por escopo + preprocessor sklearn |
| `baseline.py` | CLI de treinamento: DummyClassifier + Logistic Regression |
| `BASELINE.md` | Resultados numéricos do experimento baseline |

---

## Escopos de modelo

O pipeline respeita a hierarquia multi-tenant da plataforma:

| Escopo | `--tenant` | `--project` | Dados usados | Experimento MLflow |
|---|---|---|---|---|
| `global` | - | - | Todos os tenants | `global/baseline` |
| `tenant` | sim | - | Só esse tenant | `{tenant}/baseline` |
| `project` | sim | sim | Só esse projeto | `{tenant}/{project}/baseline` |

> Escopo define onde o modelo foi treinado/catalogado. Produção não é definida por `scope`; produção é definida por `churn.project_model_config`.

---

## Uso

O treinamento deve rodar pelo serviço Docker `trainer`, para usar a rede interna do Compose e o volume de artefatos do MLflow.

```bash
# Escopo global
docker compose --profile tools run --rm trainer python ml/baseline.py
docker compose --profile tools run --rm trainer python ml/baseline.py --dry-run

# Escopo tenant
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant <tenant-slug>
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant <tenant-slug> --dry-run

# Escopo project
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant <tenant-slug> --project <project-slug>
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant <tenant-slug> --project <project-slug> --dry-run
```

### Dry-run

O flag `--dry-run` executa treino e avaliação completos, mas não grava nada:

- Sem criação de runs no MLflow
- Sem insert em `churn.models`
- Imprime o payload exato que seria gravado

Use para validar configuração antes de comprometer resultados.

---

## Pré-requisitos

1. Serviços Docker rodando: `docker compose up -d`
2. Migrações aplicadas: `cd db && ./sqitch deploy`
3. Tenant e projeto existentes no banco (seed aplicado)
4. Variáveis de ambiente configuradas (`.env`)

---

## O que é registrado

### MLflow

- Parâmetros: tipo do modelo, folds, estratégia de CV, class_weight
- Métricas: F1, ROC-AUC, Recall, Precision (média e desvio padrão dos 5 folds)
- Artefato do modelo em `artifact_path="model"`

### churn.models

`churn.models` é o catálogo técnico de modelos treinados. Todos os modelos do run são registrados, não apenas o melhor:

| Situação | Status técnico |
|---|---|
| Melhor modelo do run (maior F1) | `approved` |
| Demais modelos do run | `trained` |

Cada registro inclui:

- `scope` derivado dos argumentos CLI
- `tenant_id` / `project_id` de acordo com o escopo (NULL para global)
- `version` auto-incremental: `v1`, `v2`, ... por `(scope, tenant_id, project_id, name)`
- `mlflow_run_id` para rastreabilidade
- Métricas do cross-validation (F1, ROC-AUC, Recall, Precision)

`status='approved'` indica que o modelo é tecnicamente elegível para servir. Isso não significa que ele esteja em produção.

### churn.project_model_config

`churn.project_model_config` é a fonte de verdade da produção por projeto:

- `model_id` aponta para o modelo aprovado que será servido.
- `is_active=true` indica a configuração atualmente ativa do projeto.
- Apenas uma configuração ativa por projeto é permitida (índice único parcial no banco).

A API resolve o modelo com cascade: configuração do projeto → configuração do tenant → modelo global (`churn.models` com `scope='global'`). O `scope` do modelo treinado não determina onde ele pode ser servido — isso é definido pela configuração em `project_model_config`.

---

## Resultados do baseline

Ver [BASELINE.md](BASELINE.md) para os números completos.

| Modelo | F1 | ROC-AUC | Recall |
|---|---|---|---|
| DummyClassifier | 0.2413 | 0.4828 | 24.2% |
| **Logistic Regression** | **0.6379** | **0.8575** | **80.7%** |

Para comparação entre todos os experimentos: [MODEL_COMPARISON.md](../MODEL_COMPARISON.md).
