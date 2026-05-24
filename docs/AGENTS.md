# AGENTS.md

Contexto do projeto para agentes de IA. Leia antes de qualquer tarefa.

---

## O que é este projeto

Plataforma de machine learning end-to-end para previsão de churn de clientes em arquitetura multi-tenant. O dataset base é o IBM Telco Customer Churn (~7k clientes). O fluxo vai da ingestão de dados até uma API de inferência com log de predições e análise de custo.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Banco de dados | PostgreSQL 16 (porta 5434 no host) |
| Migrações | Sqitch (wrapper Docker em `db/sqitch`) |
| Experiment tracking | MLflow (porta 5000) |
| Ingestão | kagglehub + pandas + SQLAlchemy |
| EDA | Jupyter + matplotlib + seaborn |
| Treinamento | scikit-learn (baseline + Random Forest + XGBoost) |
| Explicabilidade | shap>=0.45 — XGBoost nativo (`pred_contribs`) + TreeExplainer (RF) + LinearExplainer (LR) |
| Avaliação | `ml/evaluate_production.py` + `scripts/optimize_threshold.py` |
| API | FastAPI |

---

## Ambiente

```bash
# Ativar venv (WSL/Linux/Mac)
source .venv/bin/activate

# Subir serviços
docker compose up -d

# Variáveis de ambiente
cp .env.example .env
# POSTGRES_PORT=5434 (não 5432 — o Docker mapeia assim)
```

---

## Banco de dados

- Schema de negócio: `churn`
- Schema de migrações: `sqitch` (gerenciado automaticamente)
- Schema do MLflow: `public`
- Todos os PKs e FKs são **UUID** (`gen_random_uuid()`) — nunca SERIAL
- Toda tabela de negócio tem `tenant_id UUID` e `project_id UUID`
- Tenant padrão: slug `ibm-telco` | Projeto padrão: slug `telco-churn-2018`

### Tabelas

```
churn.tenants
churn.projects
churn.customers              ← dataset IBM Telco (~7k registros, split train/holdout)
churn.models                 ← statuses: candidate → approved → retired (ou rejected)
churn.model_audit_log        ← audit trail append-only de transições de status e deployment
churn.project_model_config
churn.api_keys               ← autenticação de inferência
churn.predictions            ← log de inferências (eval_batch_id + shap_values JSONB)
churn.outcomes               ← ground truth de churn real
churn.evaluation_runs        ← runs de avaliação (período, custos)
churn.evaluation_run_results ← métricas por modelo por run
churn.cost_model_config      ← configuração de custo operacional por projeto
```

Views analíticas:

```
churn.model_performance      ← consolidação de evaluation_run_results + runs
churn.evaluation_comparison  ← delta vs champion por run (F1, recall, custo)
```

### Comandos úteis

```bash
cd db && ./sqitch deploy          # aplicar migrations
psql -U churn_user -d churn_dev -h localhost -p 5434
```

---

## Convenções de código

- Código (variáveis, funções, classes) deve ser escrito em inglês
- Comentários e docstrings devem ser escritos em português
- Seguir padrões de legibilidade e boas práticas (Clean Code)
- Evitar abreviações ambíguas
- PKs sempre UUID com `DEFAULT gen_random_uuid()`
- Variáveis de ambiente via `python-dotenv` — nunca hardcoded
- Scripts Python ficam em `scripts/` (ingestão e operacional) e `ml/` (treinamento)
- Notebooks ficam em `notebooks/` — só para EDA, nunca para produção
- Modelos treinados são registrados no MLflow Model Registry e na tabela `churn.models`

---

## Restrições do agente (IA)

O agente deve respeitar as seguintes regras:

- Não executar comandos Git automaticamente (`commit`, `push`, `merge`, etc.)
- Não modificar dados diretamente no banco de dados
- Não executar comandos DDL (create, drop, alter, etc.)
- Não realizar ações destrutivas sem confirmação explícita
- Sempre sugerir mudanças antes de aplicá-las

---

## Status de implementação

| Módulo | Status |
|---|---|
| Infraestrutura (Docker + PostgreSQL + MLflow) | ✅ Completo |
| Schema multi-tenant (Sqitch — migrations 00–31) | ✅ Completo |
| Pipeline de ingestão (`scripts/load_ibm_telco.py`) | ✅ Completo |
| EDA (`notebooks/01_eda.ipynb`) | ✅ Completo |
| Relatório de negócio (`notebooks/relatorio_negocio.md`) | ✅ Completo |
| Treinamento baseline (`ml/`) — DummyClassifier + Logistic Regression | ✅ Completo |
| Random Forest (`ml/models/random_forest/`) | ✅ Completo |
| Testes automatizados (`tests/`) — unit 85%, integração 43% (isolados) | ✅ Completo |
| API de inferência (`src/`) | ✅ Completo |
| Governança de modelos (approve/reject/retire + audit log) | ✅ Completo |
| Isolamento de ciclos de avaliação (`eval_batch_id`) | ✅ Completo |
| Avaliação em produção (`ml/evaluate_production.py`) | ✅ Completo |
| Scripts operacionais (`scripts/`) | ✅ Completo |
| XGBoost (`ml/models/xgboost.py`) — champion em produção | ✅ Completo |
| Explicabilidade SHAP (`ml/explainability/`) — online via `SHAP_ENABLED` + batch com `--shap` | ✅ Completo |
| Próximos experimentos (`ml/`) — MLP PyTorch | 🔲 Pendente |

---

## Arquivos críticos

| Arquivo | Função |
|---|---|
| `docker-compose.yml` | Orquestra PostgreSQL, MLflow, API e Grafana |
| `Makefile` | Atalhos para lint, test, run, build, logs |
| `db/sqitch.conf` | Configuração do Sqitch (target: localhost:5434) |
| `db/deploy/*.sql` | Migrations de schema (00–31) |
| `ml/explainability/shap_explainer.py` | Cálculo SHAP: nativo XGBoost + TreeExplainer RF + LinearExplainer LR |
| `db/seed/001_default_tenant.sql` | Seed de tenant e projeto padrão |
| `scripts/load_ibm_telco.py` | Carga do dataset IBM Telco |
| `ml/evaluate_production.py` | Avalia predictions × outcomes, grava evaluation_run_results |
| `scripts/seed_outcomes_from_customers.py` | Popula churn.outcomes com ground truth do holdout |
| `scripts/predict_holdout_batch.py` | Envia clientes holdout para a API em lote |
| `scripts/optimize_threshold.py` | Varre thresholds para encontrar ponto ótimo de custo |
| `src/` | API de inferência FastAPI |
| `requirements.txt` | Dependências Python |
| `.env` | Variáveis de ambiente (não versionado) |
