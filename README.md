# Churn Prediction ML Platform

Plataforma de machine learning end-to-end para previsão de churn de clientes em arquitetura multi-tenant. Suporta múltiplos projetos por tenant, rastreamento de experimentos com MLflow, versionamento de modelos e log de inferências — com pipeline completo desde a ingestão de dados até a API de predição.

---

## Visão Geral

```
IBM Telco Dataset ──► churn.customers (PostgreSQL)
                              │
                              ▼
                        Ingestão & EDA
                              │
                              ▼
                  Treinamento (Baselines + MLP PyTorch)
                              │
                              ▼
                  MLflow Tracking ──► Model Registry
                              │
                              ▼
                    FastAPI (Inference API)
                              │
                              ▼
              churn.predictions + churn.cost_analysis
```

---

## Stack

| Componente | Tecnologia | Função |
|---|---|---|
| Dataset | [IBM Telco Customer Churn](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data) | Base de dados de referência (~7k clientes) |
| Banco de dados | PostgreSQL 16 | Dados de clientes, modelos, predições e análise de custo |
| Experiment tracking | MLflow 2.14 | Rastreamento de runs, métricas e artefatos de modelos |
| Migrações | Sqitch (via Docker) | Versionamento do schema do banco |
| Containerização | Docker + Docker Compose | Orquestração dos serviços |
| Ingestão | kagglehub + pandas + SQLAlchemy | Download e carga do dataset no PostgreSQL |
| API de inferência | FastAPI | _(a implementar)_ |
| Modelagem | PyTorch + Scikit-learn | _(a implementar)_ |

---

## Arquitetura de dados

O schema `churn` segue uma hierarquia de isolamento multi-tenant:

```
tenant        →  isolamento por empresa/cliente
  └── project →  isolamento por produto ou caso de uso
        ├── customers            replica fiel do schema IBM Telco (ver dataset)
        ├── models               registro de modelos (global / tenant / project)
        ├── project_model_config threshold e modelo ativo por project
        ├── predictions          log de inferências da API
        └── cost_analysis        análise de custo FP/FN por project
```

> A tabela `churn.customers` replica fielmente o schema do [IBM Telco Customer Churn Dataset](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data), incluindo todas as colunas originais com seus tipos, constraints e comentários de documentação. O campo `is_synthetic` distingue registros originais do dataset de dados gerados sinteticamente. Na versão atual, apenas dados reais do IBM Telco são utilizados — o campo está reservado para versões futuras que incorporem geração de dados sintéticos para balanceamento ou aumento do dataset.

O schema `sqitch` é gerenciado automaticamente pelo Sqitch para controle de migrações.
O schema `public` é reservado para as tabelas internas do MLflow.

---

## Pré-requisitos

| Requisito | Versão mínima |
|---|---|
| Docker Desktop | 24+ |
| Git | 2.x |
| Python | 3.10+ |

> **Ambiente recomendado (Windows):** WSL 2 com Ubuntu. Os comandos abaixo foram validados nesse ambiente. Mac e Linux funcionam nativamente sem WSL.

---

## Configuração do ambiente Python

Os componentes de ML (EDA, treinamento, API) requerem um ambiente Python isolado.

```bash
python -m venv .venv

# Linux / Mac / WSL
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Com o ambiente ativo, instale as dependências:

```bash
pip install -r requirements.txt
```

---

## Executando em dev

> **Windows:** execute os comandos no terminal WSL (recomendado).
> **Mac / Linux:** execute diretamente no terminal nativo.

### 1. Clone o repositório

```bash
git clone <url-do-repo>
cd churn-prediction-ml-platform
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
# edite .env com seus valores
```

| Variável | Descrição | Padrão |
|---|---|---|
| `POSTGRES_USER` | Usuário do PostgreSQL | — |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL | — |
| `POSTGRES_DB` | Nome do banco de dados | — |
| `POSTGRES_HOST` | Host do PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Porta exposta pelo Docker | `5434` |

### 3. Suba os serviços

```bash
docker compose up -d
```

### 4. Aguarde o PostgreSQL ficar saudável

```bash
docker compose ps
# aguarde "postgres" aparecer como healthy
```

### 5. Execute as migrações

```bash
cd db && ./sqitch deploy && cd ..
```

### 6. Popule o tenant e projeto padrão

```bash
docker exec -i churn-prediction-ml-platform-postgres-1 \
  psql -U churn_user -d churn_dev \
  < db/seed/001_default_tenant.sql
```

> Cria o tenant `ibm-telco` e o projeto `telco-churn-2018`. Operação idempotente — pode ser executada mais de uma vez sem efeito colateral.

### 7. Carregue o dataset

```bash
python pipeline/load_ibm_telco.py
```

O script baixa o dataset IBM Telco via `kagglehub` (cache local após a primeira execução), transforma e insere ~7.000 registros em `churn.customers`.

### 8. Verifique os serviços

| Serviço | URL | Credenciais |
|---|---|---|
| MLflow UI | http://localhost:5000 | — |
| PostgreSQL | localhost:5434 | conforme `.env` |

### 9. Parar o ambiente

```bash
docker compose down        # mantém os dados
docker compose down -v     # apaga volumes (reset completo)
```

---

## Migrações de banco de dados (Sqitch)

O Sqitch roda via Docker — nenhuma instalação local necessária.

```bash
cd db

./sqitch deploy            # aplica todas as migrações pendentes
./sqitch status            # exibe o estado atual
./sqitch verify            # verifica a integridade das migrações aplicadas
./sqitch revert            # reverte a última migração
./sqitch revert @ROOT      # reverte todas as migrações
```

### Criando uma nova migração

```bash
cd db
./sqitch add <nome> --note "descrição da mudança"
```

Isso cria automaticamente os três arquivos:

```
db/deploy/<nome>.sql   # script de aplicação
db/revert/<nome>.sql   # script de rollback
db/verify/<nome>.sql   # script de verificação
```

---

## Estrutura do projeto

```
churn-prediction-ml-platform/
│
├── docker-compose.yml              # orquestração dos serviços
├── .env.example                    # template de variáveis de ambiente
│
├── docker/
│   └── mlflow.Dockerfile           # MLflow + psycopg2 (driver PostgreSQL)
│
├── requirements.txt                # dependências Python do projeto
├── app/                            # API de inferência (FastAPI) — a implementar
├── data/                           # arquivos locais opcionais (não versionados)
├── ml/                             # código de treinamento e avaliação — a implementar
├── models/                         # artefatos de modelos exportados — a implementar
├── notebooks/                      # EDA e experimentos (Jupyter) — a implementar
├── tests/                          # testes automatizados — a implementar
│
├── pipeline/
│   └── load_ibm_telco.py           # download via kagglehub + bulk insert em churn.customers
│
└── db/
    ├── sqitch                      # wrapper Docker do Sqitch (sem instalação local)
    ├── sqitch.conf                 # engine, targets e configurações
    ├── sqitch.plan                 # histórico ordenado de migrações
    ├── seed/
    │   └── 001_default_tenant.sql  # tenant e projeto padrão (ibm-telco / telco-churn-2018)
    ├── deploy/                     # scripts de aplicação (forward)
    │   ├── 00_schema.sql           # criação do schema churn
    │   ├── 01_tenants.sql
    │   ├── 02_projects.sql
    │   ├── 03_customers.sql        # replica do schema IBM Telco Customer Churn
    │   ├── 04_models.sql
    │   ├── 05_project_model_config.sql
    │   ├── 06_predictions.sql
    │   └── 07_cost_analysis.sql
    ├── revert/                     # scripts de rollback
    └── verify/                     # scripts de verificação pós-deploy
```

---

## Status do projeto

| Módulo | Status |
|---|---|
| Infraestrutura (Docker + PostgreSQL + MLflow) | ✅ Completo |
| Schema multi-tenant (Sqitch migrations) | ✅ Completo |
| Pipeline de ingestão (IBM Telco → `churn.customers`) | ✅ Completo |
| EDA (notebooks/) | 🔲 A implementar |
| Treinamento (Baselines + MLP PyTorch) | 🔲 A implementar |
| MLflow Model Registry | 🔲 A implementar |
| API de inferência (FastAPI) | 🔲 A implementar |

---

## Pipeline de ingestão

O script [pipeline/load_ibm_telco.py](pipeline/load_ibm_telco.py) realiza a carga completa do dataset IBM Telco no banco de dados:

1. **Download** — baixa o arquivo `Telco_customer_churn.xlsx` via `kagglehub` com cache local
2. **Transformação** — converte `Yes/No` → `boolean`, `Zip Code` → `string`, coerce `Total Charges` para numérico
3. **Mapeamento** — 33 colunas do Excel mapeadas diretamente para `churn.customers`
4. **Carga** — bulk insert de ~7.000 registros com `chunksize=500`

O script resolve `tenant_id` e `project_id` pelo slug antes de inserir, garantindo o isolamento multi-tenant.

---

## Convenções

- Todas as tabelas de negócio ficam no schema `churn`
- Toda tabela possui `tenant_id` e `project_id` para isolamento multi-tenant
- Migrações são prefixadas com número sequencial (`00_`, `01_`, ...)
- Scripts de revert devem sempre ser o inverso exato do deploy
- Credenciais nunca são hardcoded — sempre via variáveis de ambiente

---
