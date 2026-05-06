# Guia de Modelos — Churn Prediction

Referência completa dos modelos implementados e planejados nesta plataforma.
Para cada modelo: o que é, como aprende, quando usar e suas limitações.

---

## Índice e resultados

| # | Modelo | Arquivo | F1 | ROC-AUC | Recall | Status |
|---|---|---|---|---|---|---|
| 1 | [DummyClassifier](#1-dummyclassifier) | `baseline/baseline.py` | 0.2413 | 0.4828 | 0.2424 | ✅ Implementado |
| 2 | [Logistic Regression](#2-logistic-regression) | `baseline/baseline.py` | 0.6379 | 0.8575 | 0.8074 | ✅ Implementado |
| 3 | [Random Forest](#3-random-forest) | `random_forest/random_forest.py` | — | — | — | ✅ Implementado |
| 4 | [XGBoost / LightGBM](#4-xgboost--lightgbm) | `boosting/boosting.py` | — | — | — | 🔲 Pendente |
| 5 | [LogReg + Feature Engineering](#5-logistic-regression--feature-engineering) | `baseline_fe/baseline_fe.py` | — | — | — | 🔲 Pendente |
| 6 | [MLP — Rede Neural](#6-mlp--rede-neural) | `mlp/mlp.py` | — | — | — | ⏸ Após árvores |

**Métrica de decisão primária:** F1-Score — dataset desbalanceado (26.5% churn).
Um novo modelo só substitui o atual se superar simultaneamente: F1 > 0.68, ROC-AUC > 0.88, Recall > 0.82.

---

## Pré-processamento comum a todos os modelos

Todos os modelos consomem o mesmo pipeline de `ml/core/preprocessing.py`:

```
PostgreSQL churn.customers (43 colunas brutas)
    ↓  remove IDs, localização, data leakage (churn_score, cltv, churn_reason)
19 features: 3 numéricas + 5 booleanas + 11 categóricas
    ↓  ColumnTransformer
    Numéricas   → SimpleImputer(median) + StandardScaler
    Booleanas   → passthrough (já são 0/1)
    Categóricas → SimpleImputer(most_frequent) + OneHotEncoder
    ↓
~32 colunas numéricas (após OHE expandir as categóricas)
    ↓
Modelo → P(churn) ∈ [0.0, 1.0] → threshold → churn: sim/não
```

Para ver o dataset transformado antes de treinar:
```bash
python ml/tools/export_dataset.py
# Gera: data/features_raw.csv e data/features_transformed.csv
```

---

## 1. DummyClassifier

**Arquivo:** `baseline.py` | **Tipo:** Baseline estatístico

### O que é

Não aprende nenhum padrão. Olha a proporção de churn no treino (26.5%) e sorteia
aleatoriamente respeitando essa proporção.

### Como aprende

```
Treino  → observa que 26.5% dos clientes churnam
Predição → sorteia True com probabilidade 26.5%, False com 73.5%
```

Sem pesos, sem features, sem lógica — puramente aleatório com distribuição calibrada.

### Para que serve

É o **piso absoluto de referência**. Qualquer modelo real deve bater o Dummy.
Se um modelo complexo perder para o Dummy, há bug no pipeline ou nas features.

### Não usar em produção. Nunca.

---

## 2. Logistic Regression

**Arquivo:** `baseline.py` | **Tipo:** Modelo linear clássico

### O que é

Aprende um **peso (coeficiente) para cada feature**. A predição é uma soma ponderada
comprimida pela função sigmoid para o intervalo [0, 1].

### Como aprende

```
P(churn) = sigmoid( w1×tenure + w2×monthly_charges + w3×fiber_optic + w4×month-to-month + ... )
```

Pesos positivos aumentam a probabilidade de churn, negativos diminuem.
Após o treino, os pesos são interpretáveis diretamente:

```
contract_Month-to-month  →  peso alto positivo  →  forte preditor de churn
tenure_months            →  peso negativo        →  mais tempo = menos risco
```

### Quando usar

- Quando o negócio exige **explicar** por que um cliente foi classificado como churn
- Como **baseline forte** antes de modelos mais complexos
- Datasets pequenos (< 10k registros)
- Regulação ou auditoria que exige interpretabilidade

### Limitações

- Captura apenas relações **lineares** — se a relação real for curvilínea ou depender de combinações de variáveis, o modelo perde sinal
- Não detecta automaticamente: "sênior + fibra + mês-a-mês = risco muito alto" como combinação
- Precisa de feature engineering manual para capturar interações

### Resultado no IBM Telco

```
F1: 0.6379  |  ROC-AUC: 0.8575  |  Recall: 80.7%  |  Precision: 52.7%
```

---

## 3. Random Forest

**Arquivo:** `random_forest/random_forest.py` | **Tipo:** Ensemble de árvores (bagging)

### O que é

Treina centenas de árvores de decisão **independentes e em paralelo**, cada uma num
subconjunto aleatório dos dados e das features. A predição final é a média das
probabilidades de todas as árvores.

### Como aprende

```
Dataset original
    ↓  bootstrap: amostra aleatória com reposição para cada árvore
Árvore 1: se tenure<12 E fiber → 81% churn
Árvore 2: se month-to-month E electronic_check → 74% churn
Árvore 3: se senior_citizen E sem tech_support → 69% churn
...500 árvores votando...
    ↓  média das probabilidades
P(churn) = 0.74
```

A aleatoriedade faz cada árvore cometer erros **diferentes** — na média, os erros
se cancelam e o resultado é mais robusto do que qualquer árvore individual.

### Vantagem sobre modelos lineares

Gera `feature_importances_` — você vê quais features mais influenciaram o modelo:

```
tenure_months       0.23  ←  mais importante
monthly_charges     0.18
contract_Month...   0.15
...
```

### Quando usar

- Quando interpretabilidade parcial (importância de features) é necessária
- Primeira escolha quando XGBoost parece complexo demais para o projeto
- Datasets médios (1k–1M registros)
- Robusto a outliers sem pré-processamento especial

### Limitações

- Modelos ficam grandes em memória (centenas de árvores serializadas)
- Mais lento que XGBoost em datasets grandes
- Não extrapola bem fora do range de valores do treino

### Como treinar

```bash
python ml/models/random_forest/random_forest.py --tenant ibm-telco --project telco-churn-2018
python ml/models/random_forest/random_forest.py --dry-run
python ml/models/random_forest/random_forest.py --n-estimators 300 --max-depth 10
```

### Expectativa para IBM Telco

```
F1 esperado: 0.68–0.73  |  ROC-AUC esperado: 0.87–0.91
```

---

## 4. XGBoost / LightGBM

**Arquivo:** `boosting/boosting.py` *(a implementar)* | **Tipo:** Gradient Boosting (ensemble sequencial)

### O que é

Treina árvores **sequencialmente**: cada nova árvore foca nos erros que as anteriores
cometeram. É o modelo que vence a maioria das competições de ML com dados tabulares.

### Como aprende

```
Árvore 1: faz uma predição grosseira para todos os clientes
    ↓  calcula os resíduos (onde errou e quanto)
Árvore 2: aprende a corrigir especificamente os erros da Árvore 1
    ↓  calcula os novos resíduos (menores)
Árvore 3: corrige o que Árvore 1 + Árvore 2 ainda erram
    ↓ ...
300 árvores, cada uma reduzindo o erro residual
    ↓  soma ponderada (learning rate controla o quanto cada árvore contribui)
P(churn) final
```

**XGBoost** e **LightGBM** são duas implementações do mesmo conceito.
LightGBM é geralmente mais rápido em datasets grandes (cresce a árvore por folha,
não por nível).

### Quando usar

- **Primeira escolha para dados tabulares em produção** — ponto final
- Quando o objetivo é maximizar F1/ROC-AUC sem restrição de interpretabilidade
- Lida nativamente com dados faltantes e categóricos

### Limitações

- Sensível a overfitting se mal tunado (muitas árvores + learning rate alto)
- Requer tuning de hiperparâmetros para extrair o máximo (n_estimators, max_depth, subsample...)
- Mais difícil de explicar intuitivamente do que Random Forest

### Expectativa para IBM Telco

```
F1 esperado: 0.70–0.76  |  ROC-AUC esperado: 0.89–0.93
Provavelmente o melhor resultado entre todos os modelos.
```

---

## 5. Logistic Regression + Feature Engineering

**Arquivo:** `baseline_fe/baseline_fe.py` *(a implementar)* | **Tipo:** Modelo linear com features derivadas

### O que é

O **mesmo algoritmo** da Logistic Regression (#2), mas com features novas criadas
manualmente. Testa a hipótese: *o gargalo é o modelo ou a representação dos dados?*

### Como funciona

Em vez de entregar `tenure_months=3` e `monthly_charges=85` separados, você cria:

```python
# Custo por mês de relacionamento — sinaliza clientes de alto custo e curto vínculo
df["charge_per_tenure"] = df["monthly_charges"] / (df["tenure_months"] + 1)

# Clientes novos têm comportamento de churn muito diferente dos antigos
df["is_new_customer"] = (df["tenure_months"] < 12).astype(int)

# Combinação de risco: alto gasto + sem compromisso
df["high_value_month_to_month"] = (
    (df["monthly_charges"] > 70) & (df["contract"] == "Month-to-month")
).astype(int)

# Nível de engajamento com serviços adicionais
df["num_addon_services"] = (
    df[["online_security", "online_backup", "device_protection",
        "tech_support", "streaming_tv", "streaming_movies"]] == "Yes"
).sum(axis=1)
```

### Por que testar isso

Se LogReg+FE bater o MLP, o problema não era o algoritmo — eram as features.
Isso é valioso: mantém o modelo simples e interpretável, só melhora a entrada.

### Quando usar

- Quando há hipóteses de negócio claras sobre combinações de variáveis
- Quando interpretabilidade é obrigatória e ensemble não é opção
- Como diagnóstico: se FE ajuda LogReg, vai ajudar todos os outros modelos também

### Limitações

- Processo manual e iterativo — requer conhecimento do domínio
- Risco de overfitting ao criar muitas features derivadas

---

## 6. MLP — Rede Neural

**Arquivo:** `mlp/mlp.py` *(a implementar — após árvores)* | **Tipo:** Deep Learning (PyTorch)

### O que é

Empilha múltiplas camadas de transformações não-lineares. Cada camada aprende uma
representação mais abstrata — as primeiras camadas capturam padrões simples, as
seguintes combinam esses padrões em padrões mais complexos.

### Como aprende

```
Input: ~32 features
    ↓  Linear(32→128) + BatchNorm + ReLU + Dropout(0.3)
    Camada 1: aprende "quem tem fibra", "quem tem contrato curto"...
    ↓  Linear(128→64) + BatchNorm + ReLU + Dropout(0.3)
    Camada 2: combina → "fibra + contrato curto + pagamento eletrônico"
    ↓  Linear(64→32) + ReLU
    Camada 3: comprime a representação
    ↓  Linear(32→1) + Sigmoid
Output: P(churn) ∈ [0, 1]
```

- **ReLU:** ativa só quando positivo — introduz não-linearidade entre camadas
- **BatchNorm:** normaliza ativações — treino mais estável e rápido
- **Dropout(0.3):** desliga 30% dos neurônios por batch — evita que o modelo decore o treino

### Quando usar

- Quando suspeitar de padrões complexos não-lineares que LogReg não captura
- Datasets grandes (> 50k registros idealmente — com 7k o benefício é limitado)
- Imagens, texto, áudio, séries temporais — onde redes neurais dominam

### Limitações

- **Caixa-preta:** não dá para explicar a decisão por cliente
- Mais lento para treinar do que Random Forest e XGBoost
- Para dados tabulares estruturados, tipicamente perde para XGBoost
- Requer mais tuning (learning rate, arquitetura, dropout, epochs)

---

## Como escolher o modelo para o seu problema

```
1. Precisa explicar a decisão individualmente?
       Sim → Logistic Regression (+ FE se F1 insuficiente)
       Não → continua ↓

2. Quer a melhor métrica possível em dados tabulares?
       Sim → XGBoost / LightGBM

3. Quer entender quais features mais importam?
       Sim → Random Forest

4. Suspeita de padrões muito complexos / dataset grande?
       Sim → MLP

5. Está começando / precisa de referência mínima?
       → DummyClassifier (só como piso de comparação)
```

---

## Protocolo de experimentação — o que garante comparação justa

Todos os modelos seguem obrigatoriamente:

| Etapa | Configuração |
|---|---|
| Pré-processamento | `ml/core/preprocessing.py` — `build_preprocessor()` |
| Validação | `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` |
| Métricas | F1, ROC-AUC, Recall, Precision (média ± desvio dos 5 folds) |
| Tracking | MLflow — `http://localhost:5000` |
| Registro | `churn.models` — scope, version, status |

Resultados consolidados: [`MODEL_COMPARISON.md`](../../MODEL_COMPARISON.md)
