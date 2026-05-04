# Resultados do Random Forest — Churn Prediction

**Data:** —  
**Dataset:** IBM Telco Customer Churn — 7.043 clientes  
**Churn rate:** 26.5% (classes desbalanceadas)  
**Validação:** StratifiedKFold, 5 folds, random_state=42  
**MLflow:** experimento `ibm-telco/telco-churn-2018/random-forest`

---

## Resultados

| Modelo | F1 ± std | ROC-AUC ± std | Recall | Precision |
|---|---|---|---|---|
| Random Forest | — | — | — | — |

> *A preencher após execução.*

---

## Configuração do experimento

```python
RandomForestClassifier(
    n_estimators  = 500,
    max_depth     = None,    # cresce até folhas puras
    max_features  = "sqrt",  # padrão para classificação
    class_weight  = "balanced",
    random_state  = 42,
    n_jobs        = -1,
)
```

Preprocessing idêntico ao baseline: `ml/core/preprocessing.py`.

---

## Como executar

```bash
# Dry-run (sem gravação)
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --dry-run

# Treino real
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018

# Hiperparâmetros customizados
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018 --n-estimators 300 --max-depth 10
```

---

## Expectativa

```
F1 esperado   : 0.68–0.73
ROC-AUC esperado: 0.87–0.91
```

Critério de substituição da Logistic Regression: F1 > 0.68, ROC-AUC > 0.88, Recall > 0.82 — **simultaneamente**.

---

## Top features (a preencher)

O modelo loga `feature_importances_` no MLflow como `feature_importances.json`.  
Acesse via: `http://localhost:5000` → experimento `ibm-telco/telco-churn-2018/random-forest`.
