# Testes — churn-prediction-ml-platform

Suite de testes automatizados cobrindo modelos ML, pipeline de ingestão, API de inferência e isolamento multi-tenant.

---

## Estrutura

```
tests/
├── conftest.py                          # fixture fake_customers_df (compartilhada)
│
├── unit/                                # testes unitários — sem banco, sem serviços externos
│   ├── api/
│   │   ├── test_predict_contract.py     # contrato JSON de POST /predict-churn
│   │   ├── test_admin_model_config.py   # configuração de champion/challenger
│   │   ├── test_model_resolver.py       # resolução de modelo ativo por tenant/projeto
│   │   └── test_predict_champion_challenger.py  # roteamento de tráfego champion/challenger
│   ├── ml/
│   │   ├── test_baseline.py             # DummyClassifier + Logistic Regression
│   │   ├── test_config.py               # contrato de configuração de features
│   │   ├── test_preprocessing.py        # ColumnTransformer sklearn
│   │   ├── test_risk_classification.py  # classify_risk()
│   │   ├── test_random_forest.py        # Random Forest
│   │   ├── test_train.py / test_training.py
│   │   ├── test_evaluate_production.py  # evaluate_production.py
│   │   ├── test_evaluation_comparison.py
│   │   ├── test_evaluation_reports.py
│   │   ├── test_mlp.py                  # MLP PyTorch
│   │   └── test_registry.py             # registro no MLflow + DB
│   ├── pipeline/
│   │   └── test_pipeline.py             # transform() e load() sem banco
│   └── scripts/
│       └── test_seed_outcomes.py        # seed_outcomes_from_customers.py
│
└── integration/                         # testes de integração — requerem PostgreSQL
    ├── conftest.py                      # setup automático do banco + fixtures de seed
    ├── test_health.py                   # GET /health
    ├── test_auth.py                     # API key e JWT — casos de falha
    ├── test_admin.py                    # CRUD tenant, projeto, key, champion/challenger
    ├── test_predict.py                  # POST /predict e POST /predict/batch
    ├── test_predictions_history.py      # GET /predictions (paginado)
    └── test_multitenant.py              # isolamento de dados entre tenants
```

---

## Markers

| Marker | O que valida | Como rodar |
|---|---|---|
| `smoke` | Fluxo mínimo end-to-end sem dependências externas | `pytest -m smoke` |
| `schema` | Estrutura do dataset, tipos e configuração de features | `pytest -m schema` |
| `api` | Contrato JSON da API (campos, tipos, faixas de valor) | `pytest -m api` |
| `integration` | Endpoints reais contra PostgreSQL (`churn_test`) | `pytest -m integration` |

---

## Como rodar

### Pré-requisitos

```bash
source .venv/bin/activate   # WSL / Linux / macOS
pip install -r requirements.txt
```

### Testes unitários (sem banco)

```bash
# todos os testes unitários
pytest tests/unit/

# por subdomínio
pytest tests/unit/ml/
pytest tests/unit/api/
pytest tests/unit/pipeline/

# por marker
pytest -m "smoke or schema or api"
```

### Testes de integração (requerem PostgreSQL)

```bash
# subir o banco antes
docker compose up -d postgres

# rodar
pytest tests/integration/ -m integration -v
```

O banco de testes (`churn_test`) é criado e migrado **automaticamente** na primeira execução via `integration/conftest.py`. As execuções seguintes pulam o deploy se o schema não mudou (fingerprint MD5 dos arquivos SQL).

### Todos os testes

```bash
pytest
```

### Parar na primeira falha

```bash
pytest -x
```

### Apenas os que falharam na última execução

```bash
pytest --lf
```

---

## Cobertura

O relatório HTML é gerado automaticamente em `htmlcov/` a cada execução.

```bash
# ver no terminal
pytest --cov=ml --cov=src --cov-report=term-missing

# abrir HTML
xdg-open htmlcov/index.html   # Linux/WSL
start htmlcov/index.html       # Windows
```

---

## Isolamento — o que cada camada usa

| | Banco | MLflow | API HTTP |
|---|---|---|---|
| `unit/` | Não — dados via `fake_customers_df` ou mocks | Mockado com `unittest.mock` | Não |
| `integration/` | Sim — `churn_test` (PostgreSQL 5434) | Mockado (`mlflow.sklearn.load_model`) | Sim — `TestClient` FastAPI |
