# Documentação dos Testes

Suite de testes automatizados do projeto `churn-prediction-ml-platform`.  
Cobre configuração de features, preprocessamento, regra de risco, pipeline de baseline e contrato da futura API FastAPI.

---

## Estrutura

```
tests/
├── conftest.py                        # Fixtures compartilhadas (fake_customers_df)
├── README.md                          # Esta documentação
│
├── unit/
│   ├── test_config.py                 # Contrato de configuração de features
│   ├── test_preprocessing.py          # Preprocessor sklearn + estrutura do dataset
│   ├── test_risk_classification.py    # Regra de classificação de risco de churn
│   ├── test_baseline.py               # Pipeline de treinamento, métricas, DB e MLflow
│   └── test_pipeline.py               # transform() e load() do pipeline de ingestão
│
└── api/
    └── test_predict_contract.py       # Contrato JSON de POST /predict-churn
```

> `integration/` está reservado para testes com banco e MLflow reais — não executados aqui.

---

## Tipos de Teste

| Marker | O que valida | Como rodar |
|---|---|---|
| `smoke` | Fluxo mínimo end-to-end sem dependências externas | `pytest -m smoke` |
| `schema` | Estrutura do dataset, tipos e configuração de features | `pytest -m schema` |
| `api` | Contrato JSON da API (campos, tipos, faixas de valor) | `pytest -m api` |
| *(sem marker)* | Testes unitários puros de funções isoladas | `pytest` |

---

## Pré-requisitos

```bash
# Ativar o ambiente virtual
source .venv/bin/activate          # Linux/macOS/WSL
.venv\Scripts\activate             # Windows CMD

# Instalar dependências (inclui pytest e pytest-cov)
pip install -r requirements.txt
```

---

## Passo a Passo de Uso

### 1. Rodar todos os testes

```bash
pytest
```

Saída esperada: **todos os testes passam**, relatório de cobertura no terminal e relatório HTML gerado em `htmlcov/`.

---

### 2. Rodar com verbose (ver nome de cada teste)

```bash
pytest -v
```

---

### 3. Rodar por arquivo

```bash
pytest tests/unit/test_config.py
pytest tests/unit/test_preprocessing.py
pytest tests/unit/test_risk_classification.py
pytest tests/unit/test_baseline.py
pytest tests/api/test_predict_contract.py
```

---

### 4. Rodar por tipo (marker)

```bash
# Apenas smoke tests — fluxo mínimo end-to-end
pytest -m smoke

# Apenas schema tests — estrutura e tipos de dados
pytest -m schema

# Apenas api tests — contrato de resposta JSON
pytest -m api

# Combinar markers (smoke OU schema)
pytest -m "smoke or schema"
```

---

### 5. Rodar um teste específico

```bash
pytest tests/unit/test_baseline.py::test_smoke_pipeline -v
pytest tests/unit/test_risk_classification.py::test_high_risk_at_threshold -v
```

---

### 6. Ver cobertura no terminal

```bash
pytest --cov=ml --cov-report=term-missing
```

Exemplo de saída:

```
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
ml/baseline.py             80      5    94%   107-110
ml/config.py               18      0   100%
ml/preprocessing.py        40      8    80%   45-52
ml/risk.py                 10      0   100%
-----------------------------------------------------
TOTAL                     148     13    91%
```

---

### 7. Gerar relatório HTML de cobertura

O HTML é gerado automaticamente ao rodar `pytest` (configurado em `pytest.ini`).  
Para abrir o relatório:

```bash
# Linux/macOS/WSL
open htmlcov/index.html
# ou
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

O relatório mostra **linha por linha** o que foi ou não executado durante os testes.  
Linhas em **vermelho** = não cobertas. Linhas em **verde** = cobertas.

Para gerar manualmente sem rodar os testes novamente:

```bash
pytest --cov=ml --cov-report=html:htmlcov
```

---

### 8. Verificar warnings sem suprimir

```bash
pytest -W error
```

---

### 9. Parar na primeira falha

```bash
pytest -x
```

---

### 10. Rodar apenas os testes que falharam na última execução

```bash
pytest --lf
```

---

## O que cada arquivo testa

### `conftest.py`

Define a fixture `fake_customers_df` — um `DataFrame` com 12 linhas (6 `churn=0`, 6 `churn=1`) cobrindo todas as features do IBM Telco Dataset. Usada por todos os testes que precisam de dados sem acessar o banco.

---

### `unit/test_config.py` — Schema Test

**O que garante:** a configuração de features em `ml/config.py` é um contrato estável.

| Teste | Garante |
|---|---|
| `test_target_column_is_churn_value` | `TARGET == "churn_value"` |
| `test_numeric/bool/categorical_features_not_empty` | Nenhuma lista de features está vazia |
| `test_target_not_in_any_feature_list` | Sem data leakage do target nas features de entrada |
| `test_no_overlap_between_feature_groups` | NUMERIC, BOOL e CATEGORICAL são disjuntos |
| `test_drop_cols_dont_overlap_features` | `DROP_COLS` não contamina as features de entrada |
| `test_drop_cols_exclude_target` | `TARGET` não é descartado acidentalmente |
| `test_known_*_features_present` | Features essenciais do IBM Telco continuam configuradas |

---

### `unit/test_preprocessing.py` — Schema Test + Unit

**O que garante:** o preprocessor sklearn transforma dados corretamente sem dependência de banco.

| Teste | Garante |
|---|---|
| `test_fake_dataset_has_all_expected_columns` | `[SCHEMA]` DataFrame fake tem todas as colunas necessárias |
| `test_fake_dataset_target_is_binary` | `[SCHEMA]` Target contém apenas 0 e 1 |
| `test_fake_dataset_has_both_classes` | `[SCHEMA]` Dataset não está desbalanceado ao extremo |
| `test_fake_dataset_numeric_columns_are_numeric` | `[SCHEMA]` Tipos corretos nas colunas numéricas |
| `test_build_preprocessor_returns_column_transformer` | Retorna o tipo correto do sklearn |
| `test_preprocessor_has_three_transformers` | Pipelines numeric, bool e categorical presentes |
| `test_preprocessor_transforms_fake_data` | Transforma dados sem erro, shape correto |
| `test_preprocessor_output_has_no_nan` | Imputers eliminam todos os NaN da saída |
| `test_preprocessor_handles_nulls_in_input` | Valores nulos na entrada não geram NaN na saída |
| `test_preprocessor_number_of_output_columns` | OneHotEncoder expande o número de colunas |

---

### `unit/test_risk_classification.py`

**O que garante:** `classify_risk()` em `ml/risk.py` classifica corretamente em todos os cenários.

| Teste | Garante |
|---|---|
| `test_high_risk_at/above_threshold` | `probability >= 0.8` → `"high"` |
| `test_medium_risk_at_lower/between` | `0.4 <= probability < 0.8` → `"medium"` |
| `test_low_risk_below/at_zero` | `probability < 0.4` → `"low"` |
| `test_probability_below_zero_raises` | `ValueError` para probabilidade negativa |
| `test_probability_above_one_raises` | `ValueError` para probabilidade > 1 |
| `test_custom_thresholds_*` | Thresholds customizados funcionam corretamente |
| `test_return_type_is_string` | Retorno sempre é `str` |
| `test_valid_return_values_only` | Retorno sempre em `{"low", "medium", "high"}` |

---

### `unit/test_baseline.py` — Smoke Test + Unit

**O que garante:** todo o módulo `ml/baseline.py` funciona corretamente sem banco de dados nem MLflow real.

| Grupo | Testes | Garante |
|---|---|---|
| **Smoke** | `test_smoke_pipeline*` | `[SMOKE]` Pipeline completo fit→predict→predict_proba não quebra |
| **Interface sklearn** | `test_models_have_*` | Todos os modelos em `MODELS` têm `fit`, `predict`, `predict_proba` |
| **`_derive_scope()`** | `test_derive_scope_*` | Os 3 escopos (global/tenant/project) retornam valores corretos |
| **`_cv_metrics()`** | `test_cv_metrics_*` | Retorna todas as chaves `{metric}_mean/std` como `float` |
| **`_parse_args()`** | `test_parse_args_*` | Defaults, flags CLI e erro de `--project` sem `--tenant` |
| **`_run_model()`** | `test_run_model_*` | dry_run retorna sentinel; sem dry_run chama MLflow com params e metrics |
| **`_next_version()`** | `test_next_version_*` | `count=0 → v1`, `count=3 → v4`, parâmetros corretos na query |
| **`_register_in_db()`** | `test_register_in_db_*` | dry_run não escreve no DB; status técnico faz apenas INSERT, sem controlar produção |
| **`main()`** | `test_main_*` | Chama todos os modelos; MLflow ausente no dry_run; best model marcado como `approved` |

---

### `unit/test_pipeline.py`

**O que garante:** a lógica de transformação de `pipeline/load_ibm_telco.py` funciona corretamente sem banco de dados nem Kaggle.

| Grupo | Testes | Garante |
|---|---|---|
| **Renomeação** | `test_transform_renames_all_columns_to_snake_case` | Todas as colunas originais viram snake_case via `COLUMN_MAP` |
| **Contagem** | `test_transform_row_count_unchanged` | Número de linhas não muda após transform |
| **Yes/No → bool** | `test_transform_yes/no_maps_to_*` | `"Yes"` → `True`, `"No"` → `False` |
| **Yes/No → bool** | `test_transform_all_yes_no_columns_converted` | Todas as colunas `YES_NO_COLS` contêm só `True`/`False`/NaN |
| **Yes/No → bool** | `test_transform_strips_whitespace_before_mapping` | `"  Yes  "` e `" no "` são normalizados |
| **Yes/No → bool** | `test_transform_unknown_yes_no_value_becomes_nan` | Valor desconhecido vira NaN sem quebrar |
| **Zip Code** | `test_transform_zip_code_is_string` | Zip Code vira `dtype object` (string) |
| **Zip Code** | `test_transform_zip_code_value_preserved` | Valor numérico preservado como string |
| **Total Charges** | `test_transform_total_charges_numeric_string_converted` | Strings numéricas viram `float` |
| **Total Charges** | `test_transform_total_charges_empty_string_becomes_nan` | String vazia/espaço vira NaN |
| **Total Charges** | `test_transform_total_charges_already_numeric_unchanged` | Float já numérico não é alterado |
| **Imutabilidade** | `test_transform_does_not_mutate_input` | DataFrame original não é modificado |
| **load()** | `test_load_injects_tenant/project_id` | `tenant_id` e `project_id` adicionados em todas as linhas |
| **load()** | `test_load_sets_is_synthetic_false` | `is_synthetic=False` em todos os registros |
| **load()** | `test_load_sends_only_expected_columns` | Apenas colunas de `COLUMN_MAP` + IDs de infra enviadas ao banco |
| **load()** | `test_load_calls_to_sql_with_correct_table_params` | `name="customers"`, `schema="churn"`, `if_exists="append"` |

---

### `api/test_predict_contract.py` — API Test

**O que garante:** o contrato JSON de `POST /predict-churn` está definido e pode ser validado antes da API existir.

Contrato esperado:
```json
{
  "customer_id":       "string",
  "churn_probability": 0.82,
  "risk_level":        "high",
  "prediction":        "churn",
  "threshold_used":    0.5,
  "model_version":     "v1"
}
```

| Teste | Garante |
|---|---|
| `test_predict_contract_valid_*` | `[API]` Respostas válidas (high/medium/low risk) passam na validação |
| `test_predict_contract_boundary_*` | `[API]` Probabilidades 0.0 e 1.0 são aceitas |
| `test_predict_contract_missing_required_field` | `[API]` Campo ausente lança `AssertionError` |
| `test_predict_contract_invalid_probability_*` | `[API]` Probabilidade fora de [0,1] é rejeitada |
| `test_predict_contract_invalid_risk_level` | `[API]` `risk_level` fora de `{low,medium,high}` é rejeitado |
| `test_predict_contract_invalid_prediction_value` | `[API]` `prediction` fora de `{churn,no_churn}` é rejeitado |
| `test_predict_contract_wrong_field_type` | `[API]` Tipo errado (ex: `str` em vez de `float`) é rejeitado |

---

## Isolamento — o que os testes NÃO usam

| Dependência | Status |
|---|---|
| PostgreSQL | Não usado — dados via `fake_customers_df` |
| MLflow server | Não usado — `mlflow.*` mockado |
| Kaggle / kagglehub | Não usado — sem download de dados |
| API FastAPI | Não usada — apenas contrato JSON validado |

---

## Próximos testes (quando a API for criada)

```
tests/
└── api/
    ├── test_predict_contract.py       # já existe — contrato JSON
    ├── test_predict_endpoint.py       # POST /predict-churn via httpx.AsyncClient
    └── test_health_endpoint.py        # GET /health → {"status": "ok"}

tests/
└── integration/
    ├── ml/
    │   ├── test_preprocessing_db.py   # load_data() com banco real + rollback
    │   └── test_baseline_db.py        # _register_in_db() com transação revertida
    └── pipeline/
        └── test_load_ibm_telco_db.py  # transform() + load() com banco de teste
```

Para rodar apenas testes de integração (quando implementados):
```bash
pytest tests/integration/ -v
```
