# Resultados do Random Forest — Churn Prediction

**Data:** 03/05/2026
**Dataset:** IBM Telco Customer Churn — 7.043 clientes
**Churn rate:** 26.5% (classes desbalanceadas)
**Validação:** StratifiedKFold, 5 folds, random_state=42
**MLflow:** experimento `ibm-telco/telco-churn-2018/random-forest`
**Run ID:** `1389f4884b7b47fd959b882409bff005`

---

## Resultados

| Modelo | F1 | ROC-AUC | Recall | Precision |
|---|---|---|---|---|
| Random Forest | **0.6476** | **0.8530** | 0.7666 | 0.5611 |

---

## Configuração do experimento

Script: `python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --max-depth 8 --n-estimators 100`

Parâmetros:

```
n_estimators : 100 árvores
max_depth    : 8
max_features : sqrt (padrão para classificação)
class_weight : balanced
random_state : 42
```

Preprocessing idêntico ao baseline: `ml/data/preprocessing.py`.

---

## Diagnóstico treino × teste

| Métrica | Treino | Teste | Gap | Leitura |
|---|---:|---:|---:|---|
| F1 | 0.7096 | 0.6470 | +0.0626 | Sem overfitting crítico |
| ROC-AUC | 0.9070 | 0.8579 | +0.0491 | Generalização aceitável |

Gap controlado — `max_depth=8` reduziu overfitting em relação a floresta sem limite de profundidade.

---

## Top 5 features

```
contract_Month-to-month   0.1625
tenure_months             0.1126
total_charges             0.0834
contract_Two year         0.0791
tech_support_No           0.0680
```

---

## Análise

- Random Forest superou Logistic Regression em Precision (0.5611 vs 0.5491) mas ficou abaixo em F1 (0.6476 vs 0.6586) e Recall (0.7666 vs 0.8226).
- ROC-AUC inferior ao da Logistic Regression (0.8530 vs 0.8636).
- Recall caiu de 0.8226 para 0.7666 — o modelo perde mais churners, piorando o indicador mais importante para o negócio.
- Não atingiu os thresholds para promoção: F1 > 0.68, ROC-AUC > 0.88 e Recall > 0.82 simultaneamente.

---

## Decisão

Random Forest registrado como **challenger aprovado**, não promovido a champion. Logistic Regression permanece como modelo recomendado por entregar Recall maior, desempenho praticamente equivalente em ROC-AUC e menor complexidade operacional.

---

## Como executar

```bash
# Dry-run (sem gravação)
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --dry-run

# Treino real com parâmetros do experimento
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --max-depth 8 --n-estimators 100

# Hiperparâmetros customizados
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --n-estimators 300 --max-depth 10
```
