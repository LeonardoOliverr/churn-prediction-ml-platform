# Model Comparison Report — Churn Prediction

**Projeto:** Telco Churn Prediction  
**Tenant:** IBM Telco (`ibm-telco`)  
**Dataset:** IBM Telco Customer Churn — 7.043 clientes | Churn rate: 26.5%  
**Protocolo de validação:** StratifiedKFold, 5 folds, random_state=42  
**Tracking:** MLflow — `http://localhost:5000`

> Este documento é atualizado a cada novo experimento concluído.  
> A métrica de decisão primária é o **F1-Score** (classes desbalanceadas).  
> O modelo recomendado é o que apresenta melhor equilíbrio entre F1, Recall, ROC-AUC e complexidade operacional.

---

## Resumo Executivo

| # | Modelo | F1 | ROC-AUC | Recall | Precision | Status |
|---|---|---|---|---|---|---|
| 1 | DummyClassifier (estratificado) | 0.3148 | 0.5347 | 0.3094 | 0.3203 | ✅ Concluído |
| 2 | Logistic Regression | **0.6586** | **0.8636** | **0.8226** | 0.5491 | ✅ Champion |
| 3 | Random Forest | 0.6476 | 0.8530 | 0.7666 | **0.5611** | ✅ Challenger |
| 4 | XGBoost / LightGBM | — | — | — | — | 🔲 Pendente |
| 5 | Logistic Regression + Feature Engineering | — | — | — | — | 🔲 Pendente |
| 6 | MLP — Rede Neural (PyTorch) | — | — | — | — | ⏸ Após árvores |

**Fonte das métricas:** `churn.models` — métricas registradas no treinamento (holdout de avaliação)

**Modelo recomendado atualmente:** `Logistic Regression` (`active`, scope=project)  
**Challenger atual:** `Random Forest` (`approved`, scope=project)  
**Experimento MLflow:** `ibm-telco/telco-churn-2018/baseline`  
**Guia de modelos:** [`ml/MODELS.md`](ml/MODELS.md)

---

## Critérios de Decisão

Um novo modelo só substitui o atual se superar **os três critérios simultaneamente:**

| Critério | Threshold mínimo | Justificativa |
|---|---|---|
| F1 > | 0.68 | Melhoria de pelo menos 2 pontos sobre o champion (0.6586) |
| ROC-AUC > | 0.88 | Melhoria de pelo menos 2 pontos sobre o champion (0.8636) |
| Recall > | 0.83 | Detectar mais churners que o champion (0.8226) sem regredir |

Se o modelo mais complexo não superar esses três thresholds, o modelo mais simples é mantido — menor custo de manutenção, maior interpretabilidade.

---

## Detalhamento por Experimento

---

### Experimento 1 — Baseline (DummyClassifier + Logistic Regression)
**Data:** 30/04/2026  
**MLflow:** `ibm-telco/telco-churn-2018/baseline` (experiments/5)  
**Branch:** `feat/model-training`

#### Configuração

```
Preprocessing:
  Numéricas  → SimpleImputer(median) + StandardScaler
  Booleanas  → passthrough (já 0/1)
  Categóricas → OneHotEncoder(handle_unknown="ignore")

Features: 3 numéricas + 5 booleanas + 11 categóricas = 19 colunas de entrada
Drop: churn_score (leakage), churn_reason (leakage), localização, cltv
```

#### Resultados

| Modelo | F1 | ROC-AUC | Recall | Precision |
|---|---|---|---|---|
| DummyClassifier | 0.3148 | 0.5347 | 0.3094 | 0.3203 |
| Logistic Regression | **0.6586** | **0.8636** | **0.8226** | 0.5491 |

#### Análise
- Logistic Regression entregou ROC-AUC de 0.8636 sem nenhum tuning — indica que as features têm sinal preditivo forte.
- Recall de 82.3% é o ponto alto: o modelo detecta 4 em cada 5 churners.
- Precision de 54.9% é o tradeoff esperado com `class_weight="balanced"` — prioriza Recall.

#### Decisão
Logistic Regression adotada como **champion** — piso de referência para todos os modelos subsequentes.

---

### Experimento 2 — Random Forest
**Data:** 03/05/2026  
**MLflow:** `ibm-telco/telco-churn-2018/random-forest` (experiments/6, run `1389f4884b7b47fd959b882409bff005`)  
**Branch:** `feature/random-forest-model`  
**Script:** `python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --max-depth 8 --n-estimators 100`

#### Configuração

```
Estimators : 100 árvores
Max depth  : 8
Max features: sqrt (padrão para classificação)
Class weight: balanced
```

#### Resultados

| Modelo | F1 | ROC-AUC | Recall | Precision |
|---|---|---|---|---|
| Random Forest | 0.6476 | 0.8530 | 0.7666 | 0.5611 |

#### Diagnóstico treino × teste

| Métrica | Treino | Teste | Gap | Leitura |
|---|---:|---:|---:|---|
| F1 | 0.7096 | 0.6470 | +0.0626 | Sem overfitting crítico |
| ROC-AUC | 0.9070 | 0.8579 | +0.0491 | Generalização aceitável |

#### Top 5 features

```
contract_Month-to-month   0.1625
tenure_months             0.1126
total_charges             0.0834
contract_Two year         0.0791
tech_support_No           0.0680
```

#### Análise
- Random Forest ficou abaixo da Logistic Regression em F1 (0.6476 vs 0.6586), ROC-AUC (0.8530 vs 0.8636) e Recall (0.7666 vs 0.8226).
- Ganhou apenas em Precision (0.5611 vs 0.5491) — produz menos falsos positivos por predição positiva.
- Recall caiu de 0.8226 para 0.7666, piorando a capacidade de capturar churners.
- Não atingiu os thresholds definidos para promoção: F1 > 0.68, ROC-AUC > 0.88 e Recall > 0.82 simultaneamente.
- O gap treino/teste ficou controlado, indicando que `max_depth=8` reduziu overfitting em relação a uma floresta sem limite de profundidade.

#### Decisão
Random Forest registrado como **challenger aprovado**, não promovido a champion. Logistic Regression permanece como modelo recomendado — F1, ROC-AUC e Recall superiores com menor complexidade operacional.

---

### Experimento 3 — XGBoost / LightGBM
**Data:** —  
**MLflow:** —  
**Branch:** —  
**Script:** `python ml/models/boosting.py --tenant ibm-telco --project telco-churn-2018`

#### Configuração

```
n_estimators  : 300
learning_rate : 0.05
max_depth     : 6
subsample     : 0.8
colsample     : 0.8
scale_pos_weight: ratio classes (desbalanceamento)
```

#### Resultados

| Modelo | F1 ± std | ROC-AUC ± std | Recall | Precision |
|---|---|---|---|---|
| XGBoost | — | — | — | — |
| LightGBM | — | — | — | — |

#### Expectativa
```
F1 esperado: 0.70–0.76  |  ROC-AUC esperado: 0.89–0.93
Provavelmente o melhor resultado entre todos os modelos.
```

> *A preencher após execução.*

---

### Experimento 4 — Logistic Regression + Feature Engineering
**Data:** —  
**MLflow:** —  
**Branch:** —  
**Script:** `python ml/models/baseline_fe.py --tenant ibm-telco --project telco-churn-2018`

#### Features candidatas

```python
# Custo por mês de relacionamento
charge_per_tenure       = monthly_charges / (tenure_months + 1)

# Segmentação de risco por tempo de contrato
is_new_customer         = tenure_months < 12

# Alto valor sem compromisso de longo prazo
high_value_no_contract  = (monthly_charges > 70) AND (contract == "Month-to-month")

# Nível de engajamento com serviços adicionais
num_addon_services      = soma de: online_security, online_backup,
                          device_protection, tech_support,
                          streaming_tv, streaming_movies
```

#### Resultados

| Modelo | F1 ± std | ROC-AUC ± std | Recall | Precision |
|---|---|---|---|---|
| LogReg + FE | — | — | — | — |

#### Hipótese a validar
Se LogReg+FE superar o MLP → o problema era a representação das features, não o algoritmo.
Nesse caso, as features derivadas devem ser aplicadas a todos os modelos subsequentes.

> *A preencher após execução.*

---

## Notas Técnicas

**Por que não usar Accuracy:**  
Com 73.5% de não-churn, um modelo que prevê "nunca churn" teria 73.5% de accuracy sem aprender nada. F1 e ROC-AUC são as métricas corretas para datasets desbalanceados.

**Tradeoff Recall × Precision:**  
O negócio de retenção prioriza Recall — deixar passar um churner (falso negativo) custa mais do que abordar um cliente que não ia cancelar (falso positivo). Threshold tuning pode ser aplicado após a seleção do modelo final.

**Reprodutibilidade:**  
Todos os experimentos usam `random_state=42` e `StratifiedKFold(n_splits=5, shuffle=True)`. Rodar novamente produz os mesmos resultados.
