# Relatório de Negócio — Análise de Churn
**Dataset:** IBM Telco Customer Churn | **Base:** 7.043 clientes | **Data:** Abril 2026

---

## Resumo Executivo

**1 em cada 4 clientes cancela o serviço.** A taxa de churn é de 26,5% — representando 1.869 clientes perdidos e um valor acumulado de **$7,7 milhões em CLTV** não realizado. O perfil do cliente que cancela é bem definido: chegou há pouco tempo, paga por cheque eletrônico, tem contrato mensal e usa fibra óptica. Isso significa que o problema é **previsível e tratável** antes que o cancelamento aconteça.

---

## Quem está cancelando?

O cliente com maior risco de churn tem o seguinte perfil:

| Característica | Cliente que cancela | Cliente que fica |
|---|---|---|
| Tempo médio de contrato | 10 meses | 38 meses |
| Mensalidade mediana | $80 | $64 |
| CLTV médio | $4.149 | $4.491 |

Clientes novos cancelam muito mais. A janela crítica de retenção é nos **primeiros 12 meses** de contrato.

---

## Os 5 principais fatores de churn

### 1. Tempo de contrato (tenure)
Clientes com menos de 12 meses têm risco de churn muito superior. Após 3 anos de contrato, o cancelamento se torna raro. **Fidelizar nos primeiros meses é a ação de maior impacto.**

### 2. Tipo de contrato
Contratos mensais concentram a grande maioria dos cancelamentos. Clientes com contratos anuais ou bianuais raramente cancelam — o comprometimento de longo prazo reduz o churn diretamente.

### 3. Método de pagamento — Cheque eletrônico
**45,3% dos clientes que pagam por cheque eletrônico cancelam** — mais que o dobro dos que usam débito automático (~17%). O pagamento manual sugere menor engajamento e menor barreira para cancelar.

### 4. Serviço de internet — Fibra óptica
**41,9% dos clientes de fibra óptica cancelam**, contra apenas 19% dos clientes DSL. Sendo o serviço mais caro, indica insatisfação com a relação custo-benefício ou qualidade percebida.

### 5. Perfil sênior
**41,7% dos clientes idosos cancelam**, contra 24% dos não-sêniors. Esse segmento pode ter dificuldades com o serviço ou suporte, e responde bem a atendimento dedicado.

---

## Impacto financeiro

| Métrica | Valor |
|---|---|
| Clientes perdidos | 1.869 |
| CLTV total perdido | $7.755.256 |
| CLTV médio por cliente perdido | $4.149 |

Reter **10% dos clientes em risco** representaria aproximadamente **$775.000 em valor preservado**.

---

## Recomendações

1. **Programa de onboarding nos primeiros 6 meses** — foco nos clientes novos, que são os que mais cancelam
2. **Incentivar migração para débito automático** — reduz churn e facilita a previsibilidade de receita
3. **Investigar satisfação dos clientes de fibra óptica** — NPS ou pesquisa de qualidade percebida
4. **Oferta de upgrade para contrato anual** — desconto ou benefício para clientes em contrato mensal no 3º e 6º mês
5. **Atendimento dedicado para sêniors** — canal simplificado ou suporte proativo para esse segmento

---

## Próximo passo

Com base nessa análise, está sendo desenvolvido um **modelo preditivo de churn** que identificará automaticamente os clientes com maior probabilidade de cancelamento antes que isso aconteça — permitindo ações de retenção proativas e direcionadas.
