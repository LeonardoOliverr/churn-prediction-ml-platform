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
| Treinamento | scikit-learn + PyTorch (a implementar) |
| API | FastAPI (a implementar) |

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
churn.customers        ← dataset IBM Telco (~7k registros)
churn.models
churn.project_model_config
churn.predictions
churn.cost_analysis
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
- Scripts Python ficam em `pipeline/` (ingestão) e `ml/` (treinamento)
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
| Schema multi-tenant (Sqitch) | ✅ Completo |
| Pipeline de ingestão (`scripts/load_ibm_telco.py`) | ✅ Completo |
| EDA (`notebooks/01_eda.ipynb`) | ✅ Completo |
| Relatório de negócio (`notebooks/relatorio_negocio.md`) | ✅ Completo |
| Treinamento baseline (`ml/`) — DummyClassifier + Logistic Regression | ✅ Completo |
| Testes automatizados (`tests/`) — unit, smoke, schema, api | ✅ Completo |
| API de inferência (`src/`) | ✅ Completo |

---

## Arquivos críticos

| Arquivo | Função |
|---|---|
| `docker-compose.yml` | Orquestra PostgreSQL e MLflow |
| `db/sqitch.conf` | Configuração do Sqitch (target: localhost:5434) |
| `db/deploy/*.sql` | Migrations de schema |
| `db/seed/001_default_tenant.sql` | Seed de tenant e projeto padrão |
| `scripts/load_ibm_telco.py` | Carga do dataset IBM Telco |
| `requirements.txt` | Dependências Python |
| `.env` | Variáveis de ambiente (não versionado) |
