# Resultados do Baseline — Churn Prediction

**Data:** 29/04/2026  
**Dataset:** IBM Telco Customer Churn — 7.043 clientes  
**Churn rate:** 26.5% (classes desbalanceadas)  
**Validação:** StratifiedKFold, 5 folds, random_state=42  
**MLflow:** experimento `baseline-v1`

---

## Resultados

| Modelo | F1 | ROC-AUC | Recall | Precision |
|---|---|---|---|---|
| DummyClassifier (estratificado) | 0.2413 ± 0.0014 | 0.4828 | 24.2% | 24.0% |
| **Logistic Regression** | **0.6379 ± 0.0160** | **0.8575** | **80.7%** | **52.7%** |

---

## Leitura dos números

### DummyClassifier
ROC-AUC de 0.48 — ligeiramente abaixo de 0.50 (pior que aleatório no ranking). Era esperado: ele não aprende nada, apenas reproduz a distribuição do target. Serve como zero absoluto de comparação.

### Logistic Regression
- **F1 = 0.6379** com desvio padrão de ±0.016 — estável entre os folds, sem overfitting por fold.
- **ROC-AUC = 0.8575** — excelente para um modelo linear sem nenhum tuning. Significa que o modelo separa bem churners de não-churners em qualquer threshold.
- **Recall = 80.7%** — o modelo detecta 4 em cada 5 clientes que vão cancelar. Para o negócio de retenção, esse é o número mais importante: falso negativo = churner que escapou = receita perdida.
- **Precision = 52.7%** — tradeoff esperado: metade dos clientes alertados não iam cancelar. Isso define o custo das ações de retenção (descontos, ligações desnecessárias).

---

## O piso está estabelecido

A Logistic Regression, sendo o modelo mais simples que realmente aprende, entregou resultados sólidos. Qualquer modelo mais complexo precisa superar esses números para justificar sua adoção.

| Métrica | Piso (Logistic Regression) | Meta para próximo modelo |
|---|---|---|
| F1 | 0.6379 | > 0.68 |
| ROC-AUC | 0.8575 | > 0.88 |
| Recall | 0.8074 | > 0.82 |

Se Random Forest ou XGBoost ficarem dentro de 2–3 pontos nessas métricas, a Logistic Regression vence — ela é mais rápida, mais interpretável e mais fácil de manter em produção.

---

## Configuração do experimento

```python
# Features usadas
NUMERIC     = ["tenure_months", "monthly_charges", "total_charges"]
BOOL        = ["senior_citizen", "partner", "dependents", "phone_service", "paperless_billing"]
CATEGORICAL = ["gender", "multiple_lines", "internet_service", "online_security",
               "online_backup", "device_protection", "tech_support",
               "streaming_tv", "streaming_movies", "contract", "payment_method"]

# Preprocessing
# Numéricas  → SimpleImputer(median) + StandardScaler
# Booleanas  → passthrough
# Categóricas → SimpleImputer(most_frequent) + OneHotEncoder(handle_unknown="ignore")

# Modelo
LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
```

Colunas excluídas por **data leakage**: `churn_score`, `churn_label`, `churn_reason`.  
Colunas excluídas por baixo sinal no baseline: localização (`city`, `state`, `zip_code`...), `cltv`.
