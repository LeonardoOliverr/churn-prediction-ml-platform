# Churn Prediction ML Platform

Plataforma de machine learning end-to-end para previsão de churn de clientes em arquitetura multi-tenant. Suporta múltiplos projetos por tenant, rastreamento de experimentos com MLflow, versionamento de modelos e log de inferências — com pipeline completo desde a ingestão de dados até a API de predição.

---

## Visão Geral

```
[1] INGESTÃO
    IBM Telco Dataset (~7k clientes)
    └── scripts/load_ibm_telco.py
        └── churn.customers (PostgreSQL)
                │
                ▼
[2] EXPLORAÇÃO
    notebooks/01_eda.ipynb
    └── análise de churn, preditores e segmentos de risco
                │
                ▼
[3] TREINAMENTO
    ml/models/baseline/baseline.py  (roda via Docker trainer)
    ├── MLflow      → artefatos + métricas por run
    └── churn.models → catálogo técnico
                        └── todos os modelos → status: candidate
                │
                ▼
[3.5] GOVERNANÇA
    PATCH /admin/tenants/{tenant_id}/projects/{project_id}/models/{model_id}/approve
    └── model.status: candidate → approved
        (ou reject → rejected | retire → retired)
        └── audit trail em churn.model_audit_log
                │
                ▼
[4] CONFIGURAÇÃO DE PRODUÇÃO
    churn.project_model_config
    └── define champion/challenger + threshold + split por projeto
        (um champion e no máximo um challenger ativos por projeto)
                │
                ▼
[5] INFERÊNCIA
    FastAPI  POST /predict  |  POST /predict/batch
    ├── autentica via churn.api_keys (x-api-key)
    ├── resolve modelo com split determinístico por customer_id:
    │     champion/challenger do projeto (404 explícito se não configurado)
    ├── carrega artefato do MLflow
    └── churn.predictions   → log de cada predição
                │
                ▼
[6] AVALIAÇÃO
    scripts/seed_outcomes_from_customers.py
    └── churn.outcomes ← ground truth (churn_value real dos clientes holdout)
                │
    ml/evaluate_production.py
    ├── churn.evaluation_runs          → run de avaliação (período, custos)
    ├── churn.evaluation_run_results   → métricas por modelo (F1, ROC-AUC, FPR, segmentação)
    └── churn.model_performance        → view consolidada
                │
    scripts/optimize_threshold.py
    └── varre thresholds sobre churn.predictions → custo ótimo por modelo
```

---

## Endpoints administrativos

Requerem JWT Bearer (`Authorization: Bearer <token>`). Gerado com `APP_SECRET_KEY` (HS256).

### Gerenciamento

| Método | Path | Descrição |
|---|---|---|
| POST | `/admin/tenants` | Criar tenant |
| POST | `/admin/projects` | Criar projeto |
| POST | `/admin/keys` | Gerar API key |
| DELETE | `/admin/keys/{key_id}` | Revogar API key |
| GET | `/admin/tenants/{tenant_id}/keys` | Listar API keys do tenant |

### Ciclo de vida de modelos

| Método | Path | Descrição |
|---|---|---|
| PATCH | `/admin/tenants/{t}/projects/{p}/models/{m}/approve` | `candidate` → `approved` |
| PATCH | `/admin/tenants/{t}/projects/{p}/models/{m}/reject` | `candidate` → `rejected` |
| PATCH | `/admin/tenants/{t}/projects/{p}/models/{m}/retire` | `approved` → `retired` |

### Deployment

| Método | Path | Descrição |
|---|---|---|
| GET | `/admin/tenants/{t}/projects/{p}/models/config` | Listar champion/challenger ativos |
| POST | `/admin/tenants/{t}/projects/{p}/models/{m}/champion` | Configurar champion |
| POST | `/admin/tenants/{t}/projects/{p}/models/{m}/challenger` | Configurar challenger |
| POST | `/admin/tenants/{t}/projects/{p}/models/{m}/promote` | Promover challenger a champion |
| POST | `/admin/tenants/{t}/projects/{p}/models/{m}/deactivate` | Desligar modelo da produção |

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
| API de inferência | FastAPI | Predição individual e em lote, multi-tenant |

---

## Arquitetura de dados

O schema `churn` segue uma hierarquia de isolamento multi-tenant:

```
tenant        →  isolamento por empresa/cliente
  └── project →  isolamento por produto ou caso de uso
        ├── customers               replica fiel do schema IBM Telco (split train/holdout)
        ├── models                  catálogo técnico (statuses: candidate/approved/rejected/retired)
        ├── model_audit_log         audit trail de aprovações, deployments e aposentadorias
        ├── project_model_config    configuração de produção ativa por project
        ├── api_keys                chaves de autenticação de inferência
        ├── predictions             log de inferências (eval_batch_id para isolamento de ciclos)
        ├── outcomes                ground truth de churn real (cross com predictions)
        ├── evaluation_runs         runs de avaliação (período, custos configurados)
        └── evaluation_run_results  métricas por modelo por run (F1, ROC-AUC, FPR, segmentação, promoção)
```

Views analíticas:

```
churn.model_performance      consolidação de evaluation_run_results + runs (view principal de análise)
churn.evaluation_comparison  delta vs champion por run (F1, recall, custo)
```

> A tabela `churn.customers` replica fielmente o schema do [IBM Telco Customer Churn Dataset](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data), incluindo todas as colunas originais com seus tipos, constraints e comentários de documentação. O campo `is_synthetic` distingue registros originais do dataset de dados gerados sinteticamente. Na versão atual, apenas dados reais do IBM Telco são utilizados — o campo está reservado para versões futuras que incorporem geração de dados sintéticos para balanceamento ou aumento do dataset.

O schema `sqitch` é gerenciado automaticamente pelo Sqitch para controle de migrações.
O schema `public` é reservado para as tabelas internas do MLflow.

### churn.models — catálogo técnico

`churn.models` registra todos os modelos treinados. Cada registro representa um artefato MLflow versionado e carrega seu estado técnico via `status`:

| Status | Significado |
|---|---|
| `candidate` | Recém-registrado após o treino — aguarda revisão humana |
| `approved` | Aprovado manualmente — elegível para champion/challenger |
| `rejected` | Reprovado na revisão — não pode ir a produção |
| `retired` | Descontinuado — encerrado por decisão operacional |

O pipeline de treinamento registra todos os modelos como `candidate`. A aprovação é feita manualmente via `PATCH .../approve`. Cada transição é registrada em `churn.model_audit_log` com `changed_by` e timestamp.

> `status='approved'` indica elegibilidade técnica. **Não significa que o modelo está em produção.** Produção é definida exclusivamente por `churn.project_model_config`.

### churn.project_model_config — configuração de produção

`churn.project_model_config` é a fonte de verdade sobre qual modelo está servindo cada projeto. A API de inferência resolve o modelo ativo consultando esta tabela — nunca diretamente `churn.models`.

Regras garantidas pelo banco:

- Apenas **um champion ativo** por projeto e ambiente
- No máximo **um challenger ativo** por projeto e ambiente
- O `model_id` referenciado deve existir em `churn.models`
- O `model_id` referenciado deve ter `status='approved'` para ser carregado pela API

Campos relevantes:

| Campo | Descrição |
|---|---|
| `model_id` | Modelo aprovado que será servido pelo projeto |
| `threshold` | Threshold de decisão aplicado (padrão: 0.500) |
| `role` | Papel operacional: `champion` ou `challenger` |
| `traffic_split` | Fração do tráfego enviada ao challenger. Ex.: `0.200` = 20% |
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
1º  project_model_config champion/challenger WHERE project_id = :project_id AND is_active = TRUE
        │ não encontrado
        ▼
    404 model_not_found
```

Quando há challenger ativo, a API usa `customer_id` para aplicar split determinístico — o mesmo cliente permanece no mesmo grupo durante o teste. Projeto sem champion configurado retorna 404 explícito; não há fallback para tenant nem para modelo global.

### Fluxo de promoção de modelo

```
treino → churn.models (status=approved)
                │
                │  POST /admin/projects/{project_id}/models/champion
                │  ou /models/challenger
                ▼
   churn.project_model_config
                │
                │  API resolve via cascade
                ▼
         inferência em produção
```

Ao ativar um novo champion, o champion anterior é desativado. Ao ativar um novo challenger, o challenger anterior é desativado e o champion permanece intacto. O banco permite um champion e um challenger ativos por projeto.

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
python3 -m venv venv

# Linux / Mac / WSL
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

Com o ambiente ativo, instale as dependências:

```bash
pip install -r requirements.txt
```

O arquivo `requirements.txt` instala o ambiente local completo. As imagens Docker usam arquivos menores:

| Arquivo | Uso |
|---|---|
| `requirements-api.txt` | Runtime da API FastAPI |
| `requirements-ml.txt` | Serviço `trainer` e scripts de modelos |
| `requirements-pipeline.txt` | Ingestão do dataset |
| `requirements-notebooks.txt` | EDA/Jupyter |
| `requirements-dev.txt` | Testes |

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
| `APP_SECRET_KEY` | Chave de assinatura dos JWTs de admin | — |
| `JWT_EXPIRE_MINUTES` | Tempo de expiração do JWT em minutos | `30` |
| `MLFLOW_TRACKING_URI` | URI do servidor MLflow | `http://localhost:5000` |
| `DATABASE_URL` | Connection string da API (psycopg2) | — |

#### Gerando o APP_SECRET_KEY

`APP_SECRET_KEY` é a chave usada para assinar e verificar os JWTs de admin. Use um valor aleatório e longo — **nunca use o valor padrão `change-me-in-production` fora do ambiente local.**

```bash
# WSL / Linux / Mac — gera 32 bytes em hex (64 caracteres)
python -c "import secrets; print(secrets.token_hex(32))"

# alternativa com openssl
openssl rand -hex 32
```

Cole o resultado gerado no `.env`:

```env
APP_SECRET_KEY=a3f8c2e1d4b7...  # valor gerado pelo comando acima
```

> O mesmo valor configurado no `.env` deve ser usado para gerar o JWT no passo de autenticação. Se a chave mudar, todos os tokens ativos deixam de ser válidos.

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
python scripts/load_ibm_telco.py
```

O script baixa o dataset IBM Telco via `kagglehub` (cache local após a primeira execução), transforma e insere ~7.000 registros em `churn.customers`.

### 8. Verifique os serviços

| Serviço | URL | Credenciais |
|---|---|---|
| MLflow UI | http://localhost:5000 | — |
| API docs | http://localhost:8000/docs | — |
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
│   ├── api.Dockerfile              # API de inferência FastAPI
│   └── mlflow.Dockerfile           # MLflow + psycopg2 (driver PostgreSQL)
│
├── requirements.txt                # dependências Python do projeto
├── GLOSSARY.md                     # dicionário de todos os termos técnicos e de negócio
├── MODEL_COMPARISON.md             # comparativo de experimentos e critérios de decisão
├── src/                            # API de inferência (FastAPI)
│   ├── main.py                     # factory create_app() com middlewares e routers
│   ├── config.py                   # Settings via pydantic-settings
│   ├── dependencies.py             # autenticação (API key + JWT), injeção de DB
│   ├── middleware/                 # autenticação, rate limiting, logging estruturado
│   ├── routers/                    # endpoints: health, predict, predictions, admin
│   ├── schemas/                    # contratos Pydantic de entrada e saída
│   └── services/                   # model_resolver, prediction_logger
├── data/                           # arquivos locais opcionais (não versionados)
├── estudos/                        # exercícios de fixação de conceitos de ML
├── ml/                             # pipeline de treinamento multi-tenant (ver ml/README.md)
│   ├── README.md                   # documentação do módulo e resultados consolidados
│   ├── core/                       # infraestrutura genérica (logger, model_spec)
│   ├── config/
│   │   └── settings.py             # features, DROP_COLS, MLflow URI
│   ├── data/
│   │   └── preprocessing.py        # load_data() com filtro por split + build_preprocessor()
│   ├── models/
│   │   ├── baseline/               # DummyClassifier + Logistic Regression
│   │   └── random_forest/          # RandomForestClassifier
│   └── evaluate_production.py      # avaliação predictions × outcomes → evaluation_run_results
├── models/                         # artefatos de modelos exportados — a implementar
├── notebooks/
│   ├── 01_eda.ipynb                # análise exploratória completa (13 visualizações)
│   └── relatorio_negocio.md        # relatório executivo com achados e recomendações
├── tests/                          # testes automatizados (unit, smoke, schema, api)
│
├── scripts/
│   ├── seed_outcomes_from_customers.py  # popula churn.outcomes com ground truth do holdout
│   ├── predict_holdout_batch.py         # envia clientes holdout para a API em lote
│   └── optimize_threshold.py            # varre thresholds → ponto ótimo de custo por modelo
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
    │   ├── 09_models_status.sql    # status técnico (renomeado em migration 29: candidate/approved/rejected/retired)
    │   ├── 10_api_keys.sql         # tabela de API keys para autenticação de inferência
    │   ├── 11_models_status_and_project_config_semantics.sql  # semântica de produção via project_model_config
    │   ├── 12_champion_challenger.sql # champion/challenger e traffic split
    │   ├── 13_production_evaluation.sql  # coluna split em customers + tabela outcomes (base)
    │   ├── 14_holdout_evaluation.sql     # tabela outcomes (versão final com FKs)
    │   ├── 15_evaluation_runs.sql        # tabelas evaluation_runs + evaluation_run_results
    │   ├── 16_deprecate_cost_analysis.sql # deprecação de cost_analysis
    │   ├── 17_comments.sql               # COMMENTs de documentação nas tabelas
    │   └── 18_analytics_enhancements.sql # taxas derivadas, segmentação, promoção, views
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
| Random Forest (`ml/models/random_forest/`) | ✅ Completo |
| Semântica de status técnico (`churn.models`) e configuração de produção (`churn.project_model_config`) | ✅ Completo |
| API de inferência (FastAPI) — predição individual e em lote | ✅ Completo |
| Avaliação em produção — holdout split + outcomes + evaluation runs | ✅ Completo |
| Análise de custo com matriz de confusão (`churn.evaluation_run_results`) | ✅ Completo |
| Otimização de threshold (`scripts/optimize_threshold.py`) | ✅ Completo |
| Próximos experimentos (`ml/`) — XGBoost, MLP | 🔲 Pendente |

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

O script [scripts/load_ibm_telco.py](scripts/load_ibm_telco.py) realiza a carga completa do dataset IBM Telco no banco de dados:

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

O serviço `trainer` monta o volume `mlflow_artifacts` em `/mlflow/artifacts`, acessa o PostgreSQL por `postgres:5432` e usa `MLFLOW_TRACKING_URI=http://mlflow:5000`. Por isso, evite rodar scripts de treino diretamente na máquina local quando eles geram artefatos.

```bash
# escopo global — treina com dados de todos os tenants
docker compose --profile tools run --rm trainer python ml/models/baseline/baseline.py

# escopo tenant
docker compose --profile tools run --rm trainer python ml/models/baseline/baseline.py --tenant ibm-telco

# escopo project (mais específico)
docker compose --profile tools run --rm trainer python ml/models/baseline/baseline.py --tenant ibm-telco --project telco-churn-2018

# simulação sem gravar nada
docker compose --profile tools run --rm trainer python ml/models/baseline/baseline.py --tenant ibm-telco --project telco-churn-2018 --dry-run
```

Após o treino, o script registra cada modelo em `churn.models`:

- Todos os modelos do run recebem `status='candidate'`
- A aprovação é feita manualmente via `PATCH .../approve`
- Nenhum modelo é automaticamente colocado em produção

**Para colocar um modelo em produção**, use os endpoints administrativos. A API de inferência carrega o artefato MLflow em `runs:/<mlflow_run_id>/model` a partir da configuração operacional.

```bash
# configurar champion
curl -s -X POST http://localhost:8000/admin/projects/$PROJECT_ID/models/champion \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "'"$MODEL_ID"'",
    "threshold": 0.5,
    "activation_reason": "modelo aprovado para produção",
    "description": "Logistic Regression champion"
  }'

# configurar challenger com 20% do tráfego
curl -s -X POST http://localhost:8000/admin/projects/$PROJECT_ID/models/challenger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "'"$CHALLENGER_MODEL_ID"'",
    "threshold": 0.5,
    "traffic_split": 0.2,
    "activation_reason": "teste controlado",
    "description": "Random Forest challenger"
  }'
```

Resultados do baseline e critérios para os próximos experimentos: [MODEL_COMPARISON.md](MODEL_COMPARISON.md).

---

## API de Inferência

A API FastAPI roda na porta **8000** e expõe os seguintes grupos de endpoints:

| Grupo | Endpoints | Autenticação |
|---|---|---|
| Health | `GET /health`, `GET /health/ready` | Pública |
| Inferência | `POST /predict`, `POST /predict/batch` | API Key (`x-api-key`) com escopo `predict` |
| Histórico | `GET /predictions` | API Key (`x-api-key`) com escopo `predictions:read` |
| Admin | `POST /admin/tenants`, `POST /admin/projects`, `POST /admin/keys`, `DELETE /admin/keys/{id}`, `/admin/projects/{id}/models/*` | JWT Bearer |

Documentação interativa disponível em `http://localhost:8000/docs` com a API no ar.

---

### 1. Iniciar a API

```bash
# sobe o serviço api (PostgreSQL e MLflow já devem estar rodando)
docker compose up -d api

# verifica saúde
curl http://localhost:8000/health
# → {"status":"ok"}

curl http://localhost:8000/health/ready
# → {"status":"ready"}
```

---

### 2. Gerar JWT de admin

O JWT é exigido pelos endpoints `/admin/*`. Ele é assinado com `APP_SECRET_KEY` (definido no `.env`).

> **Pré-requisito:** dependências Python instaladas no venv local.
> ```bash
> pip install -r requirements.txt
> ```

#### WSL (terminal)

```bash
# na raiz do projeto, com o venv ativo
# lê APP_SECRET_KEY diretamente do .env e gera o token
TOKEN=$(python - <<'EOF'
import time, os
from jose import jwt
from dotenv import load_dotenv
load_dotenv(".env")
secret = os.environ["APP_SECRET_KEY"]
payload = {"sub": "admin", "exp": int(time.time()) + 1800}
print(jwt.encode(payload, secret, algorithm="HS256"))
EOF
)

echo $TOKEN
```

#### Python

```python
import time, os
from jose import jwt
from dotenv import load_dotenv

load_dotenv(".env")
secret = os.environ["APP_SECRET_KEY"]  # lido do .env
payload = {"sub": "admin", "exp": int(time.time()) + 1800}
token = jwt.encode(payload, secret, algorithm="HS256")
print(token)
```

---

### 3. Criar API key — `POST /admin/keys`

A API key é o segredo de autenticação para chamadas de inferência. O campo `secret` é retornado **apenas nesta resposta** — guarde-o.

> **Pré-requisito:** ter o `tenant_id` e `project_id` do tenant desejado.
> Para obter os IDs, consulte o banco:
> ```bash
> psql -U churn_user -d churn_dev -h localhost -p 5434 \
>   -c "SELECT id, slug FROM churn.tenants;"
> psql -U churn_user -d churn_dev -h localhost -p 5434 \
>   -c "SELECT id, slug FROM churn.projects;"
> ```

#### WSL (terminal)

```bash
TENANT_ID="<uuid-do-tenant>"
PROJECT_ID="<uuid-do-projeto>"   # opcional — omita para escopo de tenant

curl -s -X POST http://localhost:8000/admin/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "'"$TENANT_ID"'",
    "project_id": "'"$PROJECT_ID"'",
    "scopes": ["predict"],
    "description": "key de teste"
  }' | python -m json.tool

# guarde o campo "secret" retornado
API_KEY="churn_live_sk_..."
```

#### Python

```python
import requests

token = "..."           # JWT gerado no passo anterior
tenant_id = "..."       # UUID do tenant
project_id = "..."      # UUID do projeto (opcional)

resp = requests.post(
    "http://localhost:8000/admin/keys",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "tenant_id": tenant_id,
        "project_id": project_id,
        "scopes": ["predict"],
        "description": "key de teste",
    },
)
data = resp.json()
print(data)
api_key = data["secret"]   # guarde — retornado apenas uma vez
```

---

### 4. Predição individual — `POST /predict`

Envia as features de **um cliente** e recebe a probabilidade de churn, nível de risco e metadados do modelo.

#### WSL (terminal)

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-001",
    "tenure_months": 2,
    "monthly_charges": 94.5,
    "total_charges": 189.0,
    "senior_citizen": 0,
    "partner": 0,
    "dependents": 0,
    "phone_service": 1,
    "paperless_billing": 1,
    "gender": "Male",
    "multiple_lines": "No",
    "internet_service": "Fiber optic",
    "online_security": "No",
    "online_backup": "No",
    "device_protection": "No",
    "tech_support": "No",
    "streaming_tv": "No",
    "streaming_movies": "No",
    "contract": "Month-to-month",
    "payment_method": "Electronic check"
  }' | python -m json.tool
```

Resposta esperada:

```json
{
  "prediction_id": "...",
  "customer_id": "CUST-001",
  "churn_probability": 0.8341,
  "risk_level": "high",
  "churn_pred": true,
  "threshold_used": 0.5,
  "model_version": "1",
  "model_name": "LogisticRegression",
  "model_id": "..."
}
```

#### Python

```python
import requests

api_key = "churn_live_sk_..."

customer = {
    "customer_id": "CUST-001",
    "tenure_months": 2,
    "monthly_charges": 94.5,
    "total_charges": 189.0,
    "senior_citizen": 0,
    "partner": 0,
    "dependents": 0,
    "phone_service": 1,
    "paperless_billing": 1,
    "gender": "Male",
    "multiple_lines": "No",
    "internet_service": "Fiber optic",
    "online_security": "No",
    "online_backup": "No",
    "device_protection": "No",
    "tech_support": "No",
    "streaming_tv": "No",
    "streaming_movies": "No",
    "contract": "Month-to-month",
    "payment_method": "Electronic check",
}

resp = requests.post(
    "http://localhost:8000/predict",
    headers={"x-api-key": api_key},
    json=customer,
)
print(resp.json())
```

---

### 5. Predição em lote — `POST /predict/batch`

Envia **múltiplos clientes** (máximo 100) em uma única requisição. Com champion/challenger ativo, o modelo é resolvido por cliente usando `customer_id`; a ordem da resposta permanece igual à ordem enviada.

#### WSL (terminal)

```bash
curl -s -X POST http://localhost:8000/predict/batch \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customers": [
      {
        "customer_id": "CUST-001",
        "tenure_months": 2,
        "monthly_charges": 94.5,
        "total_charges": 189.0,
        "senior_citizen": 0,
        "partner": 0,
        "dependents": 0,
        "phone_service": 1,
        "paperless_billing": 1,
        "gender": "Male",
        "multiple_lines": "No",
        "internet_service": "Fiber optic",
        "online_security": "No",
        "online_backup": "No",
        "device_protection": "No",
        "tech_support": "No",
        "streaming_tv": "No",
        "streaming_movies": "No",
        "contract": "Month-to-month",
        "payment_method": "Electronic check"
      },
      {
        "customer_id": "CUST-002",
        "tenure_months": 58,
        "monthly_charges": 45.0,
        "total_charges": 2610.0,
        "senior_citizen": 0,
        "partner": 1,
        "dependents": 1,
        "phone_service": 1,
        "paperless_billing": 0,
        "gender": "Female",
        "multiple_lines": "Yes",
        "internet_service": "DSL",
        "online_security": "Yes",
        "online_backup": "Yes",
        "device_protection": "Yes",
        "tech_support": "Yes",
        "streaming_tv": "No",
        "streaming_movies": "No",
        "contract": "Two year",
        "payment_method": "Bank transfer (automatic)"
      }
    ]
  }' | python -m json.tool
```

#### Python

```python
import requests

api_key = "churn_live_sk_..."

batch = {
    "customers": [
        {
            "customer_id": "CUST-001",
            "tenure_months": 2, "monthly_charges": 94.5, "total_charges": 189.0,
            "senior_citizen": 0, "partner": 0, "dependents": 0,
            "phone_service": 1, "paperless_billing": 1,
            "gender": "Male", "multiple_lines": "No",
            "internet_service": "Fiber optic",
            "online_security": "No", "online_backup": "No",
            "device_protection": "No", "tech_support": "No",
            "streaming_tv": "No", "streaming_movies": "No",
            "contract": "Month-to-month",
            "payment_method": "Electronic check",
        },
        {
            "customer_id": "CUST-002",
            "tenure_months": 58, "monthly_charges": 45.0, "total_charges": 2610.0,
            "senior_citizen": 0, "partner": 1, "dependents": 1,
            "phone_service": 1, "paperless_billing": 0,
            "gender": "Female", "multiple_lines": "Yes",
            "internet_service": "DSL",
            "online_security": "Yes", "online_backup": "Yes",
            "device_protection": "Yes", "tech_support": "Yes",
            "streaming_tv": "No", "streaming_movies": "No",
            "contract": "Two year",
            "payment_method": "Bank transfer (automatic)",
        },
    ]
}

resp = requests.post(
    "http://localhost:8000/predict/batch",
    headers={"x-api-key": api_key},
    json=batch,
)
data = resp.json()
print(f"Total processado: {data['total']}")
for item in data["results"]:
    print(f"{item['customer_id']}: {item['churn_probability']:.2%} ({item['risk_level']})")
```

---

### 6. Histórico de predições — `GET /predictions`

Retorna o histórico paginado de predições do tenant/projeto da API key. O isolamento multi-tenant é garantido — não é possível acessar predições de outro tenant.

#### WSL (terminal)

```bash
# página 1, 20 itens por página (padrão)
curl -s "http://localhost:8000/predictions" \
  -H "x-api-key: $API_KEY" | python -m json.tool

# página 2, 10 itens por página
curl -s "http://localhost:8000/predictions?page=2&page_size=10" \
  -H "x-api-key: $API_KEY" | python -m json.tool
```

Resposta esperada:

```json
{
  "items": [
    {
      "id": "...",
      "customer_id": "CUST-001",
      "churn_probability": 0.8341,
      "churn_pred": true,
      "threshold_used": 0.5,
      "latency_ms": 42,
      "requested_at": "2026-05-02 14:23:11.000000+00:00",
      "model_id": "..."
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### Python

```python
import requests

api_key = "churn_live_sk_..."

resp = requests.get(
    "http://localhost:8000/predictions",
    headers={"x-api-key": api_key},
    params={"page": 1, "page_size": 20},
)
data = resp.json()
print(f"Total: {data['total']} predições")
for item in data["items"]:
    print(f"  {item['customer_id']} | {float(item['churn_probability']):.2%} | {item['requested_at']}")
```

---

### Referência rápida de campos — CustomerFeatures

| Campo | Tipo | Valores aceitos |
|---|---|---|
| `customer_id` | `string` | Identificador livre |
| `tenure_months` | `float` | Meses de contrato do cliente |
| `monthly_charges` | `float` | Valor mensal da fatura |
| `total_charges` | `float` | Total histórico cobrado |
| `senior_citizen` | `0` ou `1` | 1 = cliente sênior |
| `partner` | `0` ou `1` | 1 = possui cônjuge |
| `dependents` | `0` ou `1` | 1 = possui dependentes |
| `phone_service` | `0` ou `1` | 1 = tem serviço de telefone |
| `paperless_billing` | `0` ou `1` | 1 = fatura digital |
| `gender` | `string` | `"Male"` \| `"Female"` |
| `multiple_lines` | `string` | `"No"` \| `"Yes"` \| `"No phone service"` |
| `internet_service` | `string` | `"DSL"` \| `"Fiber optic"` \| `"No"` |
| `online_security` | `string` | `"No"` \| `"Yes"` \| `"No internet service"` |
| `online_backup` | `string` | `"No"` \| `"Yes"` \| `"No internet service"` |
| `device_protection` | `string` | `"No"` \| `"Yes"` \| `"No internet service"` |
| `tech_support` | `string` | `"No"` \| `"Yes"` \| `"No internet service"` |
| `streaming_tv` | `string` | `"No"` \| `"Yes"` \| `"No internet service"` |
| `streaming_movies` | `string` | `"No"` \| `"Yes"` \| `"No internet service"` |
| `contract` | `string` | `"Month-to-month"` \| `"One year"` \| `"Two year"` |
| `payment_method` | `string` | `"Electronic check"` \| `"Mailed check"` \| `"Bank transfer (automatic)"` \| `"Credit card (automatic)"` |

---

## Convenções

- Todas as tabelas de negócio ficam no schema `churn`
- O isolamento multi-tenant segue três escopos: `global` (sem tenant/project), `tenant` (apenas `tenant_id`) e `tenant + project` (`tenant_id` + `project_id`) — nem toda tabela possui ambas as colunas
- Migrações são prefixadas com número sequencial (`00_`, `01_`, ...)
- Scripts de revert devem sempre ser o inverso exato do deploy
- Credenciais nunca são hardcoded — sempre via variáveis de ambiente

---
