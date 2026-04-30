# Model Comparison Report — Churn Prediction

**Projeto:** Telco Churn Prediction  
**Tenant:** IBM Telco (`ibm-telco`)  
**Dataset:** IBM Telco Customer Churn — 7.043 clientes | Churn rate: 26.5%  
**Protocolo de validação:** StratifiedKFold, 5 folds, random_state=42  
**Tracking:** MLflow — `http://localhost:5000`

> Este documento é atualizado a cada novo experimento concluído.  
> A métrica de decisão primária é o **F1-Score** (classes desbalanceadas).  
> O modelo recomendado é o que apresenta o melhor F1 com complexidade justificada.

---

## Resumo Executivo

| # | Modelo | F1 | ROC-AUC | Recall | Precision | Status |
|---|---|---|---|---|---|---|
| 1 | DummyClassifier (estratificado) | 0.2413 | 0.4828 | 0.2424 | 0.2403 | ✅ Concluído |
| 2 | Logistic Regression | **0.6379** | **0.8575** | **0.8074** | 0.5273 | ✅ Concluído |
| 3 | Random Forest | — | — | — | — | 🔲 Pendente |
| 4 | XGBoost / LightGBM | — | — | — | — | 🔲 Pendente |
| 5 | Logistic Regression + Feature Engineering | — | — | — | — | 🔲 Pendente |

**Modelo recomendado atualmente:** `Logistic Regression` (`active`, scope=project)  
**Experimento MLflow:** `ibm-telco/telco-churn-2018/baseline`

---

## Critérios de Decisão

Um novo modelo só substitui o atual se superar **os três critérios simultaneamente:**

| Critério | Threshold mínimo | Justificativa |
|---|---|---|
| F1 > | 0.68 | Melhoria de pelo menos 4 pontos sobre o baseline |
| ROC-AUC > | 0.88 | Melhoria de pelo menos 3 pontos |
| Recall > | 0.82 | Detectar mais churners sem sacrificar demais a Precision |

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

| Modelo | F1 ± std | ROC-AUC ± std | Recall | Precision |
|---|---|---|---|---|
| DummyClassifier | 0.2413 ± 0.0014 | 0.4828 ± 0.0010 | 0.2424 | 0.2403 |
| Logistic Regression | **0.6379 ± 0.0160** | **0.8575 ± 0.0119** | **0.8074** | 0.5273 |

#### Análise
- Logistic Regression entregou ROC-AUC de 0.86 sem nenhum tuning — indica que as features têm sinal preditivo forte.
- Recall de 80.7% é o ponto alto: o modelo detecta 4 em cada 5 churners.
- Precision de 52.7% é o tradeoff esperado com `class_weight="balanced"` — prioriza Recall.
- Desvio padrão do F1 (±0.016) baixo — modelo estável entre os folds.

#### Decisão
Logistic Regression adotada como **piso de referência**. Próximo passo: Random Forest para verificar se não-linearidades adicionam sinal.

---

### Experimento 2 — Random Forest
**Data:** —  
**MLflow:** —  
**Branch:** —

> *A preencher após execução.*

---

### Experimento 3 — XGBoost / LightGBM
**Data:** —  
**MLflow:** —  
**Branch:** —

> *A preencher após execução.*

---

### Experimento 4 — Logistic Regression + Feature Engineering
**Data:** —  
**MLflow:** —  
**Branch:** —

> *A preencher após execução. Features candidatas: `monthly_charges / tenure_months`, reintrodução de `cltv`, agrupamento de localização por região.*

---

## Notas Técnicas

**Por que não usar Accuracy:**  
Com 73.5% de não-churn, um modelo que prevê "nunca churn" teria 73.5% de accuracy sem aprender nada. F1 e ROC-AUC são as métricas corretas para datasets desbalanceados.

**Tradeoff Recall × Precision:**  
O negócio de retenção prioriza Recall — deixar passar um churner (falso negativo) custa mais do que abordar um cliente que não ia cancelar (falso positivo). Threshold tuning pode ser aplicado após a seleção do modelo final.

**Reprodutibilidade:**  
Todos os experimentos usam `random_state=42` e `StratifiedKFold(n_splits=5, shuffle=True)`. Rodar novamente produz os mesmos resultados.
