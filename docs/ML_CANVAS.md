# ML Canvas — Churn Prediction Platform

**Projeto:** Telco Churn Prediction  
**Tenant:** IBM Telco (`ibm-telco`)  
**Versão:** 1.0 — 2026-06  
**Referência de dataset:** IBM Telco Customer Churn (~7.043 clientes)

> O ML Canvas documenta o problema de negócio antes do modelo — justificando decisões técnicas em termos de valor entregue, stakeholders afetados e consequências dos erros.

---

## Bloco 1 — Proposta de Valor

**Problema de negócio:**
Operadoras de telecomunicações enfrentam taxa de churn de ~26%, representando perda direta de receita recorrente. A abordagem reativa — tratar cancelamentos após o fato — tem custo elevado e baixo índice de reversão. Identificar clientes em risco com antecedência suficiente permite intervenção proativa antes do cancelamento.

**Proposta de valor do modelo:**
Substituir a abordagem reativa por predição antecipada de churn, priorizando intervenções por `churn_prob` e CLTV estimado. O resultado é uma lista de clientes ordenada por risco e impacto financeiro, entregue via API REST em tempo real ou em batch mensal.

**Diferencial técnico:**
- Predição com explicação SHAP em linguagem de negócio via LLM (`GET /predictions/{id}/explain`)
- Arquitetura multi-tenant: múltiplos projetos e modelos isolados no mesmo serviço
- Shadow mode e challenger routing: novos modelos testados em produção sem risco

---

## Bloco 2 — Stakeholders

| Stakeholder | Interesse principal | Métrica de sucesso |
|---|---|---|
| **Diretoria Comercial** | Reduzir churn geral e receita perdida | Churn rate mensal ↓ |
| **Time de Retenção** | Lista acionável de clientes a contatar | Precisão das indicações (Precision) |
| **Financeiro** | Custo da campanha vs. receita salva | ROI da intervenção; custo/pred ↓ |
| **TI / Dados** | Manutenção e confiabilidade do modelo | Latência p95 ≤ 500ms; uptime ≥ 99% |
| **Clientes finais** | Não ser contactado sem motivo relevante | Taxa de falsos positivos ↓ |
| **Compliance / Jurídico** | Uso ético e legal dos dados | Conformidade LGPD; explicabilidade das decisões |

---

## Bloco 3 — Entradas (Inputs)

| Feature | Tipo | Fonte |
|---|---|---|
| `tenure_months` | Numérica | CRM — histórico de contrato |
| `monthly_charges` | Numérica | Sistema de faturamento |
| `total_charges` | Numérica | Sistema de faturamento |
| `contract` | Categórica | CRM |
| `internet_service` | Categórica | Sistema de provisionamento |
| `payment_method` | Categórica | Sistema financeiro |
| `senior_citizen` | Booleana | CRM |
| `partner`, `dependents` | Booleana | CRM |
| `phone_service`, `paperless_billing` | Booleana | CRM / Portal do cliente |
| Serviços adicionais (7 features) | Booleana | Sistema de provisionamento |

**Frequência de atualização:** dados disponíveis em batch mensal via exportação do CRM, ou em tempo real para predições individuais via API.

**Features excluídas:** `churn_score`, `churn_reason`, `churn_label` (leakage), `cltv` (derivado), localização (sem sinal preditivo).

---

## Bloco 4 — Saída (Output)

| Campo | Tipo | Uso |
|---|---|---|
| `churn_pred` | Boolean | Lista de ação para o time de retenção |
| `churn_prob` | Float [0,1] | Priorização por grau de risco |
| `shap_values` | JSON | Rastreabilidade da predição por feature |
| `explanation_text` | Texto | Explicação em linguagem de negócio para analistas |
| `recommended_actions` | Texto | Ações de retenção sugeridas pelo LLM |

**Formato de entrega:**
- Tempo real: `POST /predict` (cliente individual)
- Batch: `POST /predict/batch` + `scripts/predict_holdout_batch.py`
- Explicação sob demanda: `GET /predictions/{id}/explain`

---

## Bloco 5 — Métricas Técnicas

| Métrica | Razão da escolha | Valor alvo |
|---|---|---|
| **F1-Score** | Equilíbrio precision/recall com classes desbalanceadas (26% churn) | ≥ 0.65 |
| **ROC-AUC** | Capacidade de discriminação independente de threshold | ≥ 0.85 |
| **Recall** | FN (churn não detectado) é mais caro que FP — priorizar captura | ≥ 0.75 |
| **Precision** | Evitar excesso de falsos positivos que desperdiçam recursos de retenção | ≥ 0.50 |
| **Latência p95** | Experiência do usuário na API de inferência | ≤ 500ms |

**Threshold padrão:** 0.5 (ajustável via `scripts/optimize_threshold.py` por análise de custo)

**Resultados atuais (modelos treinados):**

| Modelo | F1 | ROC-AUC | Recall | Status |
|---|---|---|---|---|
| Logistic Regression | 0.6586 | 0.8636 | 0.8226 | Aprovado |
| Random Forest | 0.6476 | 0.8530 | 0.7666 | Aprovado |
| XGBoost | — | — | — | Champion |
| MLP PyTorch | 0.6563 | 0.8676 | 0.8000 | Candidate |

---

## Bloco 6 — Métricas de Negócio

O custo operacional é calculado com base no modelo CLTV (Customer Lifetime Value):

| Tipo de erro | Fórmula de custo | Exemplo (holdout) |
|---|---|---|
| **Falso Negativo** (churner não detectado) | `FN × CLTV_médio × multiplier_FN` | ~R$ 9.608 total no holdout (RF) |
| **Falso Positivo** (não-churner abordado) | `FP × MonthlyCharges × 2 meses × desconto (20%)` | Incluso no custo total |
| **Custo/predição** | `custo_total / n_predições` | R$ 43,95 (RF champion anterior) |

**Interpretação:** FN é ~120× mais caro que FP neste contexto → threshold mais agressivo (baixo) é justificado economicamente para maximizar Recall.

**Monitoramento:** `ml/evaluate_production.py` + `churn.evaluation_run_results` + `churn.model_performance` (view analítica).

---

## Bloco 7 — Impacto dos Erros

| Erro | Consequência no negócio | Custo estimado | Frequência esperada |
|---|---|---|---|
| **Falso Negativo** | Perda total do cliente — nenhuma intervenção realizada | CLTV do cliente (R$ 1.400–R$ 8.600) | ~20% dos churners (Recall 0.80) |
| **Falso Positivo** | Custo da campanha sem necessidade; possível irritação do cliente | 2 meses × MonthlyCharges × 20% desconto (~R$ 12–80) | ~45% das predições positivas (Precision 0.55) |

**Tradeoff principal:**
Aumentar Recall (capturar mais churners) aumenta necessariamente os Falsos Positivos. O ponto ótimo é definido pelo modelo de custo e ajustado via threshold — não pela métrica F1 isolada.

**Risco de auto-realização:** threshold muito baixo contata clientes de baixo risco repetidamente, podendo induzir insatisfação e churn secundário.

---

## Bloco 8 — Dados de Treinamento

| Aspecto | Detalhe |
|---|---|
| Fonte | IBM Telco Customer Churn (público, Kaggle) |
| Volume | 7.043 registros |
| Qualidade | 11 nulos em `total_charges` (< 0,2%) — tratados via `SimpleImputer(median)` |
| Desbalanceamento | 26,5% positivos (churn = 1) — mitigado com `pos_weight` e `class_weight` |
| Split | Estratificado: 80% treino / 20% holdout (`random_state=42`) |
| Versão do dataset | Estática — snapshot 2018 sem pipeline de atualização incremental |
| Armazenamento | `churn.customers` no PostgreSQL 16 — com `tenant_id`, `project_id` e `split` |
| Validação de schema | Pandera (`ml/data/schema.py`) — valida tipos, ranges e categorias na ingestão |

---

## Bloco 9 — SLOs (Service Level Objectives)

| SLO | Valor alvo |
|---|---|
| Latência da API — p95 | ≤ 500ms |
| Latência da API — p99 | ≤ 1.000ms |
| Disponibilidade da API | ≥ 99% em horário comercial |
| Frequência de reavaliação do modelo | Mensal ou após evento relevante |
| Tempo máximo para promoção de novo champion | 5 dias úteis após detecção de degradação |
| Cobertura de outcomes reais | ≥ 90% das predições com outcome em 30 dias |
| Tempo máximo de resposta do explain LLM | ≤ 5s (primeira chamada); ≤ 100ms (cache) |

---

## Bloco 10 — Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Drift de distribuição de features** | Média | Alto | Monitoramento mensal de distribuição; alertas Grafana; retreino programado |
| **Novo produto introduz categoria desconhecida** | Baixa | Médio | `handle_unknown="ignore"` no OHE + validação Pandera na borda da API |
| **Dataset de 2018 desatualizado** | Alta (em produção real) | Alto | Documentado como limitação; substituir por dados reais com pipeline incremental |
| **Custo CLTV calculado sem dados reais** | Média | Médio | Parâmetros configuráveis em `cost_model_config`; fácil substituição |
| **Champion degradado silenciosamente** | Baixa | Alto | `evaluate_production.py` mensal + alertas F1 < 0.60 + governance em `churn.model_audit_log` |
| **Dependência da API OpenAI (explicações)** | Baixa | Baixo | Falha do LLM não interrompe predição — `explanation_text=null` com HTTP 200 |
| **Vazamento da LLM_ENCRYPTION_KEY** | Muito Baixa | Alto | Rotação da chave invalida API Keys criptografadas — procedimento documentado no `.env.example` |
