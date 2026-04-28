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
| Dataset | [IBM Telco Customer Churn](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data) | Base de dados de referência para treinamento e avaliação |
| Banco de dados | PostgreSQL 16 | Dados de clientes, modelos, predições e análise de custo |
| Experiment tracking | MLflow 2.14 | Rastreamento de runs, métricas e artefatos de modelos |
| Migrações | Sqitch (via Docker) | Versionamento do schema do banco |
| Containerização | Docker + Docker Compose | Orquestração dos serviços |
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

> `requirements.txt` será adicionado junto com os módulos de treinamento e API.

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

| Variável | Descrição |
|---|---|
| `POSTGRES_USER` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL |
| `POSTGRES_DB` | Nome do banco de dados |

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
cd db && ./sqitch deploy
```

### 6. Verifique os serviços

| Serviço | URL | Credenciais |
|---|---|---|
| MLflow UI | http://localhost:5000 | — |
| PostgreSQL | localhost:5434 | conforme `.env` |

### 7. Parar o ambiente

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
├── app/                            # API de inferência (FastAPI) — a implementar
├── data/                           # dataset bruto e processado — a implementar
├── ml/                             # código de treinamento e avaliação — a implementar
├── models/                         # artefatos de modelos exportados — a implementar
├── notebooks/                      # EDA e experimentos (Jupyter) — a implementar
├── pipeline/                       # pipeline de ingestão e feature engineering — a implementar
├── tests/                          # testes automatizados — a implementar
│
└── db/
    ├── sqitch                      # wrapper Docker do Sqitch (sem instalação local)
    ├── sqitch.conf                 # engine, targets e configurações
    ├── sqitch.plan                 # histórico ordenado de migrações
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

## Convenções

- Todas as tabelas de negócio ficam no schema `churn`
- Toda tabela possui `tenant_id` e `project_id` para isolamento multi-tenant
- Migrações são prefixadas com número sequencial (`00_`, `01_`, ...)
- Scripts de revert devem sempre ser o inverso exato do deploy
- Credenciais nunca são hardcoded — sempre via variáveis de ambiente

---
