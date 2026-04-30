# ml/ — Pipeline de Treinamento

Módulo de treinamento multi-tenant. Suporta três escopos de modelo, dry-run e registro automático em `churn.models`.

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
| `global` | — | — | Todos os tenants | `global/baseline` |
| `tenant` | ✓ | — | Só esse tenant | `{tenant}/baseline` |
| `project` | ✓ | ✓ | Só esse projeto | `{tenant}/{project}/baseline` |

> **Aviso sobre escopo global:** treina com dados de todos os tenants misturados. Útil como cold-start para tenants novos. Em produção, prefira `tenant` ou `project`.

---

## Uso

```bash
# Ativar o ambiente
source .venv/bin/activate

# Escopo global
python ml/baseline.py
python ml/baseline.py --dry-run

# Escopo tenant
python ml/baseline.py --tenant <tenant-slug>
python ml/baseline.py --tenant <tenant-slug> --dry-run

# Escopo project
python ml/baseline.py --tenant <tenant-slug> --project <project-slug>
python ml/baseline.py --tenant <tenant-slug> --project <project-slug> --dry-run
```

### Dry-run

O flag `--dry-run` executa treino e avaliação completos, mas **não grava nada**:
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
- **Parâmetros:** tipo do modelo, folds, estratégia de CV, class_weight
- **Métricas:** F1, ROC-AUC, Recall, Precision (média e desvio padrão dos 5 folds)

### churn.models
**Todos os modelos do run** são registrados (não apenas o melhor):

| Situação | Status atribuído |
|---|---|
| Melhor modelo do run (maior F1) | `active` |
| Demais modelos do run | `shadow` |
| `active` anterior ao novo `active` | `archived` (automático, mesma transação) |

Cada registro inclui:
- `scope` derivado dos argumentos CLI
- `tenant_id` / `project_id` de acordo com o escopo (NULL para global)
- `version` auto-incremental: `v1`, `v2`, ... por `(scope, tenant_id, project_id, name)`
- `mlflow_run_id` para rastreabilidade
- Métricas do cross-validation (F1, ROC-AUC, Recall, Precision)

**Invariante garantida pelo banco:** no máximo um `active` por `(scope, tenant_id, project_id, name)`.

> **Próximos passos:** resolver de modelo com fallback automático `project → tenant → global` para a camada de inferência.

---

## Resultados do baseline

Ver [BASELINE.md](BASELINE.md) para os números completos.

| Modelo | F1 | ROC-AUC | Recall |
|---|---|---|---|
| DummyClassifier | 0.2413 | 0.4828 | 24.2% |
| **Logistic Regression** | **0.6379** | **0.8575** | **80.7%** |

Para comparação entre todos os experimentos: [MODEL_COMPARISON.md](../MODEL_COMPARISON.md).
