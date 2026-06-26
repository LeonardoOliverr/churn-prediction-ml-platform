# Model Card — Churn Prediction Platform

**Versão:** 1.0  
**Data:** 2026-06  
**Mantido por:** Time de ML — IBM Telco Churn Project  
**Repositório:** `churn-prediction-ml-platform`

---

## 1. Visão Geral do Modelo

| Campo | Valor |
|---|---|
| Nome | Churn Prediction Ensemble + MLP |
| Tipo | Classificação binária supervisionada |
| Objetivo | Prever probabilidade de cancelamento (churn) de clientes de telecom |
| Champion atual | XGBoost (`mlp-pytorch` registrado como candidate) |
| Frameworks | PyTorch (MLP), scikit-learn (XGBoost, RF, LR) |
| Dataset base | IBM Telco Customer Churn — 7.043 clientes |
| Threshold padrão | 0.5 (ajustável via `optimize_threshold.py`) |
| API de inferência | `POST /predict` e `POST /predict/batch` |
| Rastreabilidade | MLflow + `churn.models` + `churn.predictions` |

---

## 2. Uso Pretendido (Intended Use)

### Uso pretendido

- Identificar clientes com alto risco de cancelamento em operadoras de telecomunicações
- Alimentar campanhas de retenção proativa com lista priorizada por `churn_prob`
- Subsidiar decisões do time comercial com explicações SHAP em linguagem de negócio
- Comparar modelos em produção via shadow mode e challenger routing

### Uso não pretendido

- **Recusar serviços** a clientes com base na predição — o modelo identifica risco, não elegibilidade
- **Substituir julgamento humano** em casos de alto impacto individual (rescisão contratual, ações legais)
- **Aplicar a outros setores** sem retreinamento — calibrado para telecom B2C com perfil IBM Telco
- **Usar como único critério** de decisão — sempre combinar com análise de contexto do cliente

---

## 3. Dados de Treinamento

| Aspecto | Detalhe |
|---|---|
| Fonte | IBM Telco Customer Churn (Kaggle — dataset público) |
| Volume total | 7.043 clientes |
| Split treino | 5.634 registros (80% estratificado) |
| Split holdout | 1.409 registros (20% estratificado) |
| Período | Snapshot único — sem dados temporais explícitos |
| Desbalanceamento | 26,5% churners (1.869) vs 73,5% não-churners (5.174) |

### Features utilizadas

| Grupo | Features |
|---|---|
| Numéricas (3) | `tenure_months`, `monthly_charges`, `total_charges` |
| Booleanas (5) | `senior_citizen`, `partner`, `dependents`, `phone_service`, `paperless_billing` |
| Categóricas (11) | `gender`, `multiple_lines`, `internet_service`, `online_security`, `online_backup`, `device_protection`, `tech_support`, `streaming_tv`, `streaming_movies`, `contract`, `payment_method` |

### Features excluídas e motivo

| Feature | Motivo da exclusão |
|---|---|
| `churn_score`, `churn_reason`, `churn_label` | Data leakage — só disponíveis após o churn |
| `cltv` | Derivado de tenure e charges; não adiciona sinal independente |
| Localização (`country`, `city`, `zip_code`, etc.) | Sem valor preditivo baseline para este dataset |

### Pré-processamento

```
Numéricas  → SimpleImputer(median) + StandardScaler
Booleanas  → passthrough (já 0/1)
Categóricas → OneHotEncoder(handle_unknown="ignore")
Resultado  → 41 features após OHE
```

---

## 4. Métricas de Avaliação

**Protocolo:** StratifiedKFold 5-fold (sklearn); val set 80/20 (MLP PyTorch)  
**Métrica primária:** F1-Score — equilíbrio entre Precision e Recall em dataset desbalanceado

| Modelo | F1 | ROC-AUC | Recall | Precision | Status |
|---|---|---|---|---|---|
| DummyClassifier | 0.3148 | 0.5347 | 0.3094 | 0.3203 | Baseline |
| Logistic Regression | 0.6586 | 0.8636 | 0.8226 | 0.5491 | Aprovado |
| Random Forest | 0.6476 | 0.8530 | 0.7666 | 0.5611 | Aprovado |
| XGBoost | — | — | — | — | **Champion (produção)** |
| MLP PyTorch | 0.6563 | 0.8676 | 0.8000 | 0.5564 | Candidate |

> Métricas do XGBoost disponíveis no MLflow: `ibm-telco/telco-churn-2018/xgboost`

### Critérios de promoção a champion

Um modelo só substitui o champion se superar **os três critérios simultaneamente:**

| Critério | Threshold |
|---|---|
| F1 | > 0.68 |
| ROC-AUC | > 0.88 |
| Recall | > 0.83 |

### Por que não usar Accuracy

Com 73,5% de não-churners, um modelo que prediz "nunca churn" teria 73,5% de accuracy sem aprender nada. F1 e ROC-AUC são as métricas corretas para datasets desbalanceados.

---

## 5. Análise de Vieses (Bias Analysis)

### Viés de representação temporal

O dataset é um **snapshot único de 2018** — não captura sazonalidade, tendências de mercado ou mudanças de comportamento ao longo do tempo. Clientes com `tenure_months` muito curto (< 2 meses) tendem a ter churn elevado e podem distorcer predições para novos clientes.

### Viés geográfico

O dataset IBM Telco é provavelmente calibrado para o mercado norte-americano. Valores de `monthly_charges` e `total_charges` não refletem mercados com moeda ou estrutura tarifária diferente. O modelo CLTV de custo deve ser recalibrado para outros mercados.

### Viés de seleção — `SeniorCitizen`

O campo `senior_citizen` é binário (0/1) sem granularidade de faixa etária. Clientes sênior (65+) são tratados como grupo homogêneo, o que pode levar a intervenções de retenção inadequadas para subgrupos com perfis distintos.

### Risco de auto-realização

Modelos com threshold baixo (alto recall) contactam clientes que não cancelariam espontaneamente. Contato excessivo pode gerar insatisfação e induzir o churn que pretendia evitar — especialmente em clientes de baixo risco que se sentem monitorados.

### Desbalanceamento tratado

O desbalanceamento (26,5% churn) é mitigado com:
- `pos_weight=2.7` no MLP e `scale_pos_weight=2.7` no XGBoost
- `class_weight="balanced"` no Random Forest e Logistic Regression
- `StratifiedKFold` no cross-validation

---

## 6. Limitações Conhecidas

| Limitação | Impacto | Mitigação |
|---|---|---|
| Dataset único (~7k registros) | Alta variância em modelos profundos; MLP pode sofrer overfitting | Dropout(0.3) + early stopping + validação estratificada |
| Snapshot sem temporalidade | Drift não detectável na estrutura atual | Monitoramento mensal de distribuição de features |
| CLTV estimado (não real) | Custo operacional aproximado — não reflete perdas reais do negócio | Substituir por CLTV real em produção via integração CRM |
| Threshold fixo em 0.5 (padrão) | Pode ser subótimo dependendo do custo de FN vs FP do negócio | Recalibrar com `scripts/optimize_threshold.py` |
| Ausência de features comportamentais | Não captura padrões de uso (volume de chamadas, consumo de dados) | Feature engineering futuro com dados de uso real |
| Modelo estático (sem retreino incremental) | Degradação silenciosa com mudanças de mercado | Retreino periódico via `ml.train` + avaliação em `churn.evaluation_runs` |

---

## 7. Cenários de Falha (Failure Modes)

| Cenário | Sintoma | Consequência | Ação recomendada |
|---|---|---|---|
| **Drift de distribuição** | `monthly_charges` médio cresce com inflação | Modelo subestima churn de clientes caros | Monitorar distribuição mensal; retreinar |
| **Novo produto ou serviço** | `internet_service` ganha nova categoria | `handle_unknown="ignore"` silencia o erro → predição degradada | Validar schema na ingestão (Pandera) |
| **Mudança regulatória** | Contratos mensais tornam-se obrigatórios por lei | `contract` perde poder preditivo — feature mais importante zerando | Retreinar com nova distribuição |
| **Data poisoning** | Registros duplicados ou corrompidos na ingestão | Métricas infladas no holdout; champion errado promovido | Validação Pandera no pipeline de ingestão |
| **Champion degradado em produção** | Recall cai abaixo de 0.70 em `evaluation_run_results` | Churners não detectados → perda de receita silenciosa | Alertas no Grafana + promoção de challenger |
| **SHAP indisponível** | `SHAP_ENABLED=false` ou erro no explainer | Explicação LLM não gerada; `explanation_text=null` | Fallback documentado; predição continua normalmente |

---

## 8. Plano de Monitoramento

| Métrica monitorada | Frequência | Alerta |
|---|---|---|
| F1 e Recall do champion em produção | Mensal (`evaluate_production.py`) | F1 < 0.60 em janela de 30 dias |
| Custo por predição (modelo CLTV) | Mensal | Custo/pred > 2× baseline |
| Taxa de predições positivas | Semanal | Drift > ±15% em relação à média histórica |
| Cobertura de outcomes reais | Mensal | > 10% de predições sem outcome em 30 dias |
| Latência da API (p95) | Contínuo (`LoggingMiddleware`) | p95 > 500ms |
| Distribuição de `churn_prob` | Mensal | KL divergence vs distribuição de treino > 0.1 |

### Ferramentas

- `ml/evaluate_production.py` — avalia predictions × outcomes reais
- `scripts/optimize_threshold.py` — recalibra threshold por custo
- `churn.evaluation_runs` + `churn.evaluation_run_results` — histórico auditável
- `churn.model_audit_log` — rastreabilidade de promoções e deprecações

### Frequência de retreino recomendada

**Mensal** (ou imediato após eventos relevantes: novo produto, mudança regulatória, F1 < threshold de alerta).

---

## 9. Considerações Éticas

- O modelo **não deve ser usado como critério único** para negar serviços, aplicar penalidades ou tomar decisões com impacto legal sobre clientes
- **Contatos de retenção devem ser opt-out** — clientes devem poder recusar abordagens proativas sem penalidade
- **Auditar periodicamente** se o modelo penaliza desproporcionalmente grupos demográficos específicos (`senior_citizen`, clientes com `dependents`, clientes de menor renda estimada por `monthly_charges`)
- **Transparência interna:** resultados de predição devem ser acompanhados por `churn_prob` e explicações SHAP — não apenas o label binário — para que analistas humanos possam questionar o modelo
- **Dados de terceiros:** o dataset IBM Telco é público e anonimizado. Em produção real, coletar e processar dados de clientes requer conformidade com LGPD/GDPR e política de privacidade da operadora
- **Explicabilidade:** o endpoint `GET /predictions/{id}/explain` entrega explicações em linguagem de negócio via LLM, reduzindo a opacidade das decisões baseadas no modelo
