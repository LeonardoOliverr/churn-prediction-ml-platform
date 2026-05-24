# Glossário — Churn Prediction ML Platform

Referência centralizada de todos os termos técnicos e de negócio utilizados neste projeto.  
Organizado em seções temáticas para facilitar a consulta durante a leitura de qualquer documento ou código.

---

## Índice

1. [Negócio e Domínio](#1-negócio-e-domínio)
2. [Machine Learning — Conceitos Fundamentais](#2-machine-learning--conceitos-fundamentais)
3. [Machine Learning — Métricas de Avaliação](#3-machine-learning--métricas-de-avaliação)
4. [Machine Learning — Algoritmos](#4-machine-learning--algoritmos)
5. [Machine Learning — Técnicas e Problemas](#5-machine-learning--técnicas-e-problemas)
6. [Pipeline e Pré-processamento](#6-pipeline-e-pré-processamento)
7. [Infraestrutura e Experiment Tracking](#7-infraestrutura-e-experiment-tracking)
8. [Banco de Dados e Arquitetura](#8-banco-de-dados-e-arquitetura)

---

## 1. Negócio e Domínio

---

### Churn
> O cancelamento ou abandono de um cliente. Um cliente "churnou" quando encerrou o contrato ou parou de usar o serviço.

**No projeto:** coluna `churn_value` (0 = permaneceu, 1 = cancelou). Taxa de churn do dataset IBM Telco: ~26.5%.

**Por que importa:** reter um cliente existente custa 5–7x menos do que adquirir um novo. Prever churn com antecedência permite ações de retenção proativas.

---

### Churn Rate
> Percentual de clientes que cancelaram em um determinado período sobre o total de clientes ativos.

**Fórmula:** `churn_rate = clientes_que_cancelaram / total_clientes`

**No projeto:** 26.5% — isso cria um problema de **classes desbalanceadas** que afeta a escolha das métricas de avaliação.

---

### Churner
> Um cliente classificado (ou previsto) como propenso a cancelar. Termo informal usado no contexto de modelos preditivos de retenção.

---

### Retenção
> Conjunto de ações tomadas para evitar que um cliente cancele — descontos, ligações proativas, upgrade de plano, ofertas personalizadas.

**Custo de retenção:** toda ação tem um custo. Por isso Precision importa — evita desperdiçar recursos em clientes que não iam cancelar de qualquer forma.

---

### CLTV — Customer Lifetime Value
> Valor financeiro total esperado de um cliente durante todo o período de relacionamento com a empresa.

**No projeto:** coluna `cltv` no banco. Foi **excluída** do baseline porque é calculada externamente (IBM SPSS) a partir de dados que incluem a propensão de churn, o que poderia introduzir viés não controlado.

---

### Churn Score
> Pontuação de 0 a 100 calculada pelo IBM SPSS Modeler indicando a probabilidade de churn de um cliente.

**No projeto:** coluna `churn_score`. **Excluída por data leakage** — foi calculada usando o próprio dado de churn como referência. Usar esta coluna no treino inflaria artificialmente as métricas.

---

### Tenant
> Uma organização ou empresa que utiliza a plataforma de forma isolada das demais. Cada tenant tem seus próprios dados, modelos e configurações.

**No projeto:** tabela `churn.tenants`. O tenant padrão é `ibm-telco`.

**Por que existe:** a plataforma foi projetada para suportar múltiplos clientes (multi-tenant) sem que os dados de um vazem para o outro.

---

## 2. Machine Learning — Conceitos Fundamentais

---

### Feature (Variável de Entrada)
> Uma coluna do dataset usada como entrada para o modelo — uma característica que descreve um cliente ou evento.

**Exemplos no projeto:** `tenure_months`, `monthly_charges`, `contract`, `internet_service`.

**Tipos de features:**
- **Numéricas:** valores contínuos ou discretos (`tenure_months`, `monthly_charges`)
- **Booleanas:** verdadeiro/falso (`senior_citizen`, `partner`)
- **Categóricas:** categorias sem ordem natural (`contract`, `payment_method`)

---

### Target (Variável Alvo)
> A coluna que o modelo deve aprender a prever. É o "y" em qualquer equação de ML supervisionado.

**No projeto:** `churn_value` (0 ou 1).

---

### Label
> Sinônimo de target em problemas de classificação. Cada registro tem um "rótulo" que indica a classe à qual pertence.

**No projeto:** `churn_label` ("Yes"/"No") é a versão textual do target `churn_value`. Foi **excluída** por ser redundante com o target.

---

### Baseline
> Um modelo simples que estabelece o desempenho mínimo esperado. Todo modelo mais complexo deve superar o baseline para justificar sua existência.

**No projeto:** dois baselines foram implementados — `DummyClassifier` (zero absoluto) e `Logistic Regression` (piso inteligente).

---

### Cross-Validation (Validação Cruzada)
> Técnica para avaliar um modelo dividindo o dataset em múltiplos subconjuntos (folds). O modelo é treinado em alguns folds e avaliado nos restantes, repetindo o processo até que cada fold tenha sido usado como conjunto de validação.

**Vantagem sobre train/test split único:** produz uma estimativa mais confiável do desempenho real, com desvio padrão para medir a estabilidade.

**No projeto:** `StratifiedKFold(n_splits=5)` — 5 folds estratificados.

---

### StratifiedKFold
> Variante do cross-validation que garante que a proporção das classes (ex: 26.5% churn) seja mantida em cada fold.

**Por que usar:** com dados desbalanceados, um fold aleatório pode ter 10% de churners e outro 45%, tornando as métricas de cada fold incomparáveis.

---

### Fold
> Um dos subconjuntos criados durante o cross-validation. Com 5 folds, o dataset é dividido em 5 partes iguais. Em cada iteração, 4 partes treinam o modelo e 1 parte o avalia.

---

### Overfitting (Sobreajuste)
> Quando o modelo aprende os dados de treino tão bem que perde a capacidade de generalizar para dados novos. O modelo "memoriza" em vez de "aprender".

**Sinal:** métricas excelentes no treino, péssimas na validação.

---

### Underfitting (Subajuste)
> Quando o modelo é simples demais para capturar os padrões do dataset. Performa mal tanto no treino quanto na validação.

**Sinal:** métricas fracas em treino e validação simultaneamente.

---

### Hiperparâmetro
> Um parâmetro de configuração do modelo que é definido **antes** do treino (não aprendido pelos dados).

**Exemplos:** número de árvores em um Random Forest (`n_estimators`), profundidade máxima de uma árvore (`max_depth`), taxa de aprendizado (`learning_rate`).

**Contraste com parâmetros:** os pesos internos de um modelo (coeficientes da Logistic Regression, por exemplo) são **parâmetros** — aprendidos durante o treino.

---

### Classes Desbalanceadas (Imbalanced Classes)
> Situação em que uma classe do target tem muito mais exemplos do que outra.

**No projeto:** 73.5% não-churn vs. 26.5% churn. Isso torna a **accuracy** uma métrica enganosa e exige uso de F1, ROC-AUC e `class_weight`.

---

### Threshold (Limiar de Decisão)
> O valor de probabilidade acima do qual o modelo classifica um cliente como "churn". O padrão é 0.5, mas pode ser ajustado para priorizar Recall (mais baixo) ou Precision (mais alto).

**Threshold tuning:** processo de ajustar esse valor após o treinamento para otimizar a métrica de negócio relevante.

---

## 3. Machine Learning — Métricas de Avaliação

---

### Accuracy (Acurácia)
> Percentual de previsões corretas sobre o total de previsões.

**Fórmula:** `(TP + TN) / (TP + TN + FP + FN)`

**Por que não usamos:** com 73.5% de não-churn, um modelo que prevê "nunca churn" para todo mundo teria 73.5% de accuracy sem aprender nada útil.

---

### Precision (Precisão)
> Dos clientes que o modelo classificou como churn, qual porcentagem realmente cancelou.

**Fórmula:** `TP / (TP + FP)`

**No negócio:** controla o custo das ações de retenção. Precision baixa = desperdício de recursos com clientes que não iam cancelar.

---

### Recall (Revocação / Sensibilidade)
> Dos clientes que realmente cancelaram, qual porcentagem o modelo conseguiu identificar.

**Fórmula:** `TP / (TP + FN)`

**No negócio:** prioridade máxima em retenção. Um falso negativo (churner não detectado) = receita perdida.

---

### F1-Score
> Média harmônica entre Precision e Recall. Penaliza modelos que sacrificam um em favor do outro.

**Fórmula:** `2 * (Precision * Recall) / (Precision + Recall)`

**Quando usar:** principal métrica para dados desbalanceados onde tanto Precision quanto Recall importam.

---

### ROC-AUC (Area Under the ROC Curve)
> Mede a capacidade do modelo de separar churners de não-churners em **todos os thresholds possíveis**. Valor entre 0 e 1, onde 0.5 = previsão aleatória e 1.0 = separação perfeita.

**Vantagem:** independe do threshold — permite comparar modelos antes de decidir o ponto de corte ideal.

**No projeto:** usado em conjunto com F1 para ter uma visão completa da qualidade do modelo.

---

### Matriz de Confusão (Confusion Matrix)
> Tabela que mostra os 4 resultados possíveis de uma classificação binária.

|  | Previsto: Não Churn | Previsto: Churn |
|---|---|---|
| **Real: Não Churn** | TN (Verdadeiro Negativo) | FP (Falso Positivo) |
| **Real: Churn** | FN (Falso Negativo) | TP (Verdadeiro Positivo) |

- **TP:** churner corretamente identificado
- **TN:** não-churner corretamente identificado
- **FP:** falso alarme — cliente abordado desnecessariamente
- **FN:** churner que escapou — receita perdida

---

## 4. Machine Learning — Algoritmos

---

### DummyClassifier
> Classificador que não aprende nada dos dados — serve apenas como referência mínima.

**Estratégia `stratified`:** prevê classes aleatoriamente respeitando a distribuição do target (26.5% churn, 73.5% não-churn).

**No projeto:** zero absoluto do baseline. Qualquer modelo real deve superar suas métricas.

---

### Logistic Regression (Regressão Logística)
> Modelo linear que aprende a probabilidade de um evento (churn = 1) a partir de uma combinação ponderada das features.

**Por que é um bom baseline:** simples, rápido, interpretável. Estabelece o que é possível extrair com o mínimo de complexidade.

**`class_weight="balanced"`:** ajusta os pesos das classes para compensar o desbalanceamento. Sem isso, o modelo tenderia a prever "nunca churn" para minimizar o erro geral.

---

### Random Forest
> Conjunto (ensemble) de árvores de decisão treinadas em subamostras aleatórias do dataset. A previsão final é a média (ou voto majoritário) de todas as árvores.

**Vantagem sobre Logistic Regression:** captura não-linearidades e interações entre features.

**No projeto:** próximo candidato após o baseline.

---

### XGBoost / LightGBM
> Algoritmos de gradient boosting — constroem árvores sequencialmente, onde cada árvore corrige os erros da anterior.

**Por que é forte em dados tabulares:** geralmente o teto de performance em datasets estruturados como o IBM Telco.

**No projeto:** avaliado após Random Forest, somente se justificar a complexidade adicional.

---

## 5. Machine Learning — Técnicas e Problemas

---

### Data Leakage (Vazamento de Dados)
> Situação em que informação do futuro (ou derivada do target) vaza para o treino do modelo, inflando artificialmente as métricas. O modelo "cola na prova" e falha em produção.

**Tipos:**
- **Leakage direto:** usar o próprio target como feature (`churn_label` junto com `churn_value`)
- **Leakage temporal:** usar dados que só existem após o evento que se quer prever (`churn_reason`)
- **Leakage derivado:** usar features calculadas a partir do target (`churn_score`)

**No projeto:** três colunas foram excluídas por leakage — `churn_score`, `churn_label` e `churn_reason`.

---

### Feature Engineering
> Processo de criar ou transformar features existentes para melhorar a capacidade preditiva do modelo.

**Exemplos futuros para este projeto:**
- `monthly_charges / tenure_months` → custo relativo por mês de tenure
- Agrupamento de localização por região
- Reintroduzir `cltv` com controle de viés

---

### StandardScaler
> Transforma features numéricas para ter média 0 e desvio padrão 1.

**Por que usar com Logistic Regression:** modelos lineares são sensíveis à escala. Sem normalização, uma feature com valores na casa dos milhares domina o modelo sobre uma feature na casa das dezenas.

**Fórmula:** `z = (x - média) / desvio_padrão`

---

### OneHotEncoder
> Transforma uma feature categórica em múltiplas colunas binárias — uma por categoria.

**Exemplo:** a coluna `contract` com valores `Month-to-month`, `One year`, `Two year` vira três colunas binárias.

**`handle_unknown="ignore"`:** valores desconhecidos em produção são ignorados em vez de causar erro.

---

### SimpleImputer
> Preenche valores nulos (NaN) com uma estatística calculada a partir dos dados de treino.

**Estratégia `median`:** usada para `total_charges` — resistente a outliers, adequada para distribuições assimétricas.

**Estratégia `most_frequent`:** usada para categóricas — preenche com a categoria mais comum.

---

### ColumnTransformer
> Aplica transformações diferentes em grupos de colunas diferentes dentro de um único objeto sklearn.

**No projeto:** numéricas recebem `StandardScaler`, booleanas passam direto (`passthrough`), categóricas recebem `OneHotEncoder`.

---

### Pipeline (sklearn)
> Encadeia múltiplas etapas de transformação e um modelo final em um único objeto. Garante que o mesmo preprocessing aplicado no treino seja aplicado automaticamente na inferência.

**Benefício:** evita o erro mais comum em ML — aplicar transformações diferentes no treino e em produção.

---

## 6. Pipeline e Pré-processamento

---

### Ingestão
> Processo de coletar dados de uma fonte externa e carregá-los no banco de dados do sistema.

**No projeto:** `scripts/load_ibm_telco.py` baixa o dataset IBM Telco via kagglehub e insere em `churn.customers`.

---

### Preprocessing
> Conjunto de transformações aplicadas aos dados brutos para deixá-los em formato adequado para o modelo — imputação de nulos, encoding de categóricas, normalização de numéricas.

**No projeto:** `ml/preprocessing.py` centraliza todo o preprocessing reutilizável.

---

### Artifact (Artefato)
> Qualquer arquivo produzido por um experimento de ML — modelo serializado, gráficos, datasets de validação, relatórios.

**No projeto:** o MLflow armazena o pipeline sklearn completo (preprocessor + classifier) como artefato de cada run.

---

## 7. Infraestrutura e Experiment Tracking

---

### MLflow
> Plataforma open-source para rastreamento de experimentos de machine learning. Permite logar parâmetros, métricas e artefatos de cada execução e comparar resultados entre experimentos.

**No projeto:** roda na porta `5000` via Docker. Interface acessível em `http://localhost:5000`.

---

### Experiment (Experimento MLflow)
> Um agrupamento lógico de runs relacionados. Todos os modelos treinados para o mesmo objetivo ficam no mesmo experimento.

**No projeto:** experimento `churn-baseline` agrupa todos os runs do baseline.

---

### Run (Execução MLflow)
> Uma única execução de treinamento registrada no MLflow — com seus parâmetros, métricas e artefatos associados.

**No projeto:** cada chamada a `mlflow.start_run()` cria um run novo. O DummyClassifier e a Logistic Regression são runs separados dentro do experimento `churn-baseline`.

---

### MLflow Model Registry
> Repositório centralizado dentro do MLflow para versionar e gerenciar modelos prontos para produção.

**No projeto:** o melhor modelo do baseline é registrado como `churn-baseline`. Pode ser carregado em qualquer script com `mlflow.sklearn.load_model("models:/churn-baseline/latest")`.

---

### Experiment Tracking
> Prática de registrar sistematicamente os parâmetros, métricas e artefatos de cada experimento para permitir comparação e reprodutibilidade.

**Por que importa:** sem tracking, é impossível saber qual configuração produziu o melhor resultado ou reproduzir um experimento de semanas atrás.

---

## 8. Banco de Dados e Arquitetura

---

### Multi-tenant
> Arquitetura onde um único sistema serve múltiplos clientes (tenants) com isolamento de dados entre eles.

**No projeto:** toda tabela de negócio tem `tenant_id` e `project_id` para garantir que os dados de um tenant nunca sejam visíveis para outro.

---

### Schema
> Agrupamento lógico de tabelas dentro de um banco de dados PostgreSQL.

**No projeto:**
- `churn` — tabelas de negócio (customers, models, predictions, etc.)
- `sqitch` — tabelas de controle de migrações (gerenciado automaticamente)
- `public` — tabelas do MLflow

---

### Migration (Migração)
> Script SQL versionado que define ou altera o schema do banco de dados de forma controlada e rastreável.

**No projeto:** gerenciado pelo Sqitch. Cada migration fica em `db/deploy/` e pode ser aplicada com `cd db && ./sqitch deploy`.

---

### Sqitch
> Ferramenta de gerenciamento de migrações SQL baseada em dependências — não em timestamps. Cada migration declara de quais outras migrations ela depende.

**No projeto:** wrapper Docker em `db/sqitch`. Configurado para o target `localhost:5434`.

---

### UUID
> Universally Unique Identifier — identificador de 128 bits gerado de forma que a probabilidade de colisão é praticamente zero.

**No projeto:** todos os PKs e FKs usam UUID com `DEFAULT gen_random_uuid()`. Nunca SERIAL ou AUTO_INCREMENT.

**Por que UUID e não SERIAL:** em sistemas multi-tenant e distribuídos, IDs sequenciais podem colidir entre tenants ou entre instâncias. UUIDs são seguros por design.

---

*Última atualização: fase de baseline (`ml/`) — abril 2026.*
