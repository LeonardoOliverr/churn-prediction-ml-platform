# Churn Prediction ML Platform

Plataforma de machine learning end-to-end para previsão de churn de clientes em arquitetura multi-tenant. Suporta múltiplos projetos por tenant, rastreamento de experimentos com MLflow, versionamento de modelos e log de inferências — com pipeline completo desde a ingestão de dados até a API de predição.

---

## Visão Geral

```
[1] INGESTÃO
    IBM Telco Dataset (~7k clientes)
    └── pipeline/load_ibm_telco.py
        └── churn.customers (PostgreSQL)
                │
                ▼
[2] EXPLORAÇÃO
    notebooks/01_eda.ipynb
    └── análise de churn, preditores e segmentos de risco
                │
                ▼
[3] TREINAMENTO
    ml/baseline.py  (roda via Docker trainer)
    ├── MLflow      → artefatos + métricas por run
    └── churn.models → catálogo técnico
                        ├── melhor modelo  → status: approved
                        └── demais modelos → status: trained
                │
                │  promoção manual
                │  INSERT em churn.project_model_config
                ▼
[4] CONFIGURAÇÃO DE PRODUÇÃO
    churn.project_model_config
    └── define modelo ativo + threshold por projeto
        (única config ativa por projeto — garantido pelo banco)
                │
                ▼
[5] INFERÊNCIA
    FastAPI  POST /predict  |  POST /predict/batch
    ├── autentica via churn.api_keys (x-api-key)
    ├── resolve modelo com cascade:
    │     1º project_model_config do projeto  (API key com project_id)
    │     2º project_model_config do tenant   (API key sem project_id)
    │     3º churn.models scope=global        (modelo global aprovado)
    ├── carrega artefato do MLflow
    ├── churn.predictions   → log de cada predição
    └── churn.cost_analysis → análise de custo FP/FN
```

---

## Stack

| Componente | Tecnologia | Função |
|---|---|---|
| Dataset | [IBM Telco Customer Churn](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data) | Base de dados de referência (~7k clientes) |
| Banco de dados | PostgreSQL 16 | Dados de clientes, modelos, predições e análise de custo |
| Experiment tracking | MLflow 3.11.1 | Rastreamento de runs, métricas e artefatos de modelos |
| Migrações | Sqitch (via Docker) | Versionamento do schema do banco |
| Containerização | Docker + Docker Compose | Orquestração dos serviços |
| Ingestão | kagglehub + pandas + SQLAlchemy | Download e carga do dataset no PostgreSQL |
| EDA | Jupyter + matplotlib + seaborn + scikit-learn | Análise exploratória e relatório de negócio |
| Modelagem | Scikit-learn | Baseline: DummyClassifier + Logistic Regression |
| Modelagem (deep learning) | PyTorch | _(a implementar)_ |
| API de inferência | FastAPI | _(a implementar)_ |

---

## Arquitetura de dados

O schema `churn` segue uma hierarquia de isolamento multi-tenant:

```
tenant        →  isolamento por empresa/cliente
  └── project →  isolamento por produto ou caso de uso
        ├── customers            replica fiel do schema IBM Telco (ver dataset)
        ├── models               catálogo técnico de modelos treinados
        ├── project_model_config configuração de produção ativa por project
        ├── predictions          log de inferências da API
        └── cost_analysis        análise de custo FP/FN por project
```

> A tabela `churn.customers` replica fielmente o schema do [IBM Telco Customer Churn Dataset](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data), incluindo todas as colunas originais com seus tipos, constraints e comentários de documentação. O campo `is_synthetic` distingue registros originais do dataset de dados gerados sinteticamente. Na versão atual, apenas dados reais do IBM Telco são utilizados — o campo está reservado para versões futuras que incorporem geração de dados sintéticos para balanceamento ou aumento do dataset.

O schema `sqitch` é gerenciado automaticamente pelo Sqitch para controle de migrações.
O schema `public` é reservado para as tabelas internas do MLflow.

### churn.models — catálogo técnico

`churn.models` registra todos os modelos treinados. Cada registro representa um artefato MLflow versionado e carrega seu estado técnico via `status`:

| Status | Significado |
|---|---|
| `trained` | Modelo recém-registrado após o treino |
| `validated` | Modelo avaliado e testado manualmente |
| `approved` | Elegível para servir em produção |
| `archived` | Descontinuado — não deve ser selecionado |

O pipeline de treinamento (`ml/baseline.py`) atribui `approved` ao modelo de melhor F1 do run e `trained` aos demais. A promoção entre status (`trained → validated → approved`) é uma decisão operacional, feita manualmente ou via automação.

> `status='approved'` indica elegibilidade técnica. **Não significa que o modelo está em produção.** Produção é definida exclusivamente por `churn.project_model_config`.

### churn.project_model_config — configuração de produção

`churn.project_model_config` é a fonte de verdade sobre qual modelo está servindo cada projeto. A API de inferência resolve o modelo ativo consultando esta tabela — nunca diretamente `churn.models`.

Regras garantidas pelo banco:

- Apenas **uma configuração `is_active=true`** por projeto (índice único parcial)
- O `model_id` referenciado deve existir em `churn.models`
- O `model_id` referenciado deve ter `status='approved'` para ser carregado pela API

Campos relevantes:

| Campo | Descrição |
|---|---|
| `model_id` | Modelo aprovado que será servido pelo projeto |
| `threshold` | Threshold de decisão aplicado (padrão: 0.500) |
| `is_active` | `true` = configuração atualmente em produção |
| `environment` | `production`, `staging` ou `dev` |
| `configured_by` | Identificador de quem ativou a configuração |
| `activation_reason` | Motivo operacional da ativação |

### Resolução de modelo em produção (cascade)

A API resolve qual modelo carregar seguindo três níveis em ordem de especificidade:

```
API Key com project_id
        │
        ▼
1º  project_model_config WHERE project_id = :project_id AND is_active = TRUE
        │ não encontrou
        ▼
2º  project_model_config WHERE tenant_id = :tenant_id AND is_active = TRUE
    (config ativa mais recente do tenant — API key sem project_id)
        │ não encontrou
        ▼
3º  churn.models WHERE scope = 'global' AND status = 'approved'
    (modelo global aprovado mais recente)
        │ não encontrou
        ▼
    404 model_not_found
```

O nível 3 consulta `churn.models` diretamente — é o único caso em que a API não passa por `project_model_config`. O threshold aplicado nesse caso é o padrão (`0.5`).

### Fluxo de promoção de modelo

```
treino → churn.models (status=approved)
                │
                │  INSERT em project_model_config
                │  com is_active=true
                ▼
   churn.project_model_config
                │
                │  API resolve via cascade
                ▼
         inferência em produção
```

Ao ativar uma nova configuração, a anterior deve ter `is_active` definido como `false` e `deactivated_at` preenchido. O banco garante que apenas uma configuração ativa existe por projeto via índice único parcial.

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

Os componentes locais de ML (EDA, ingestão e testes) requerem um ambiente Python isolado.
O treinamento de modelos deve rodar pelo serviço Docker `trainer`, para usar a mesma rede do PostgreSQL/MLflow e o mesmo volume de artefatos.

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

O Compose também define o serviço `trainer`, usado para jobs de treinamento. Ele fica no profile `tools` e não sobe no `docker compose up -d` padrão.

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
├── GLOSSARY.md                     # dicionário de todos os termos técnicos e de negócio
├── MODEL_COMPARISON.md             # comparativo de experimentos e critérios de decisão
├── app/                            # API de inferência (FastAPI) — a implementar
├── data/                           # arquivos locais opcionais (não versionados)
├── estudos/                        # exercícios de fixação de conceitos de ML
├── ml/                             # pipeline de treinamento multi-tenant (ver ml/README.md)
│   ├── README.md                   # documentação do módulo e uso da CLI
│   ├── config.py                   # constantes e feature lists
│   ├── preprocessing.py            # carregamento com filtro por escopo + preprocessor sklearn
│   ├── baseline.py                 # treino, avaliação e registro (CLI multi-tenant)
│   └── BASELINE.md                 # resultados do experimento baseline
├── models/                         # artefatos de modelos exportados — a implementar
├── notebooks/
│   ├── 01_eda.ipynb                # análise exploratória completa (13 visualizações)
│   └── relatorio_negocio.md        # relatório executivo com achados e recomendações
├── tests/                          # testes automatizados (unit, smoke, schema, api)
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
    │   ├── 07_cost_analysis.sql
    │   ├── 08_models_unique_constraint.sql
    │   ├── 09_models_status.sql    # status técnico: trained, validated, approved, archived
    │   └── 11_models_status_and_project_config_semantics.sql  # semântica de produção via project_model_config
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
| EDA (`notebooks/`) | ✅ Completo |
| Baseline multi-tenant (`ml/`) — DummyClassifier + Logistic Regression | ✅ Completo |
| Semântica de status técnico (`churn.models`) e configuração de produção (`churn.project_model_config`) | ✅ Completo |
| API de inferência (FastAPI) — predição individual e em lote | 🔲 Em progresso |
| Próximos experimentos (`ml/`) — Random Forest, XGBoost | 🔲 Pendente |
| Análise de custo (`churn.cost_analysis`) | 🔲 Pendente |

---

## EDA e relatório de negócio

O notebook [notebooks/01_eda.ipynb](notebooks/01_eda.ipynb) contém 13 análises exploratórias do dataset IBM Telco, cobrindo:

- Distribuição de churn (~26,5% de cancelamento)
- Missing values e correlações entre variáveis numéricas
- Principais preditores: `tenure_months`, `contract`, `payment_method`, `internet_service`, `monthly_charges`
- Segmentos de risco: clientes novos, usuários de fibra óptica, pagamento por cheque eletrônico e sêniors
- Validação do `churn_score` IBM SPSS contra o `churn_value` real

Para rodar o notebook:

```bash
source .venv/bin/activate
jupyter notebook notebooks/
```

O [notebooks/relatorio_negocio.md](notebooks/relatorio_negocio.md) traduz os achados técnicos em linguagem executiva, com impacto financeiro ($7,7M em CLTV em risco) e recomendações de retenção.

---

## Pipeline de ingestão

O script [pipeline/load_ibm_telco.py](pipeline/load_ibm_telco.py) realiza a carga completa do dataset IBM Telco no banco de dados:

1. **Download** — baixa o arquivo `Telco_customer_churn.xlsx` via `kagglehub` com cache local
2. **Transformação** — converte `Yes/No` → `boolean`, `Zip Code` → `string`, coerce `Total Charges` para numérico
3. **Mapeamento** — 33 colunas do Excel mapeadas diretamente para `churn.customers`
4. **Carga** — bulk insert de ~7.000 registros com `chunksize=500`

O script resolve `tenant_id` e `project_id` pelo slug antes de inserir, garantindo o isolamento multi-tenant.

---

## Treinamento de modelos (ml/)

O módulo `ml/` implementa o pipeline de treinamento com suporte nativo a multi-tenant.
Os jobs de treino rodam pelo serviço Docker `trainer`, separado da API, para manter o isolamento de responsabilidades:

```
trainer  → treina modelos e registra métricas/artefatos no MLflow
mlflow   → armazena runs, métricas e artefatos
api      → carrega modelos registrados para inferência
postgres → armazena dados, catálogo de modelos e logs de predição
```

O serviço `trainer` monta o volume `mlflow_artifacts` em `/mlflow/artifacts`, acessa o PostgreSQL por `postgres:5432` e usa `MLFLOW_TRACKING_URI=http://mlflow:5000`. Por isso, evite rodar `ml/baseline.py` diretamente na máquina local para treinos que geram artefatos.

```bash
# escopo global — treina com dados de todos os tenants
docker compose --profile tools run --rm trainer python ml/baseline.py

# escopo tenant
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant ibm-telco

# escopo project (mais específico)
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant ibm-telco --project telco-churn-2018

# simulação sem gravar nada
docker compose --profile tools run --rm trainer python ml/baseline.py --tenant ibm-telco --project telco-churn-2018 --dry-run
```

Após o treino, o script registra cada modelo em `churn.models`:

- O modelo com maior F1 do run recebe `status='approved'`
- Os demais modelos do run recebem `status='trained'`
- Nenhum modelo é automaticamente colocado em produção

**Para colocar um modelo em produção**, é necessário criar um registro em `churn.project_model_config` apontando para o `model_id` desejado com `is_active=true`. A API de inferência carrega o artefato MLflow em `runs:/<mlflow_run_id>/model` a partir dessa configuração.

```sql
INSERT INTO churn.project_model_config
    (tenant_id, project_id, model_id, threshold, is_active, environment, configured_by, activation_reason)
VALUES (
    (SELECT tenant_id FROM churn.projects WHERE id = '<project_id>'),
    '<project_id>',
    '<model_id>',   -- deve ter status='approved' em churn.models
    0.500,
    TRUE,
    'production',
    'seu-identificador',
    'motivo da ativação'
);
```

Resultados do baseline e critérios para os próximos experimentos: [MODEL_COMPARISON.md](MODEL_COMPARISON.md).

---

## Convenções

- Todas as tabelas de negócio ficam no schema `churn`
- Toda tabela possui `tenant_id` e `project_id` para isolamento multi-tenant
- Migrações são prefixadas com número sequencial (`00_`, `01_`, ...)
- Scripts de revert devem sempre ser o inverso exato do deploy
- Credenciais nunca são hardcoded — sempre via variáveis de ambiente

---
