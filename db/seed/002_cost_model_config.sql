-- Seed: configuração de custo real para o projeto IBM Telco
--
-- Modo cltv:
--   FN cost = cltv × 1.0             (100% do valor do cliente perdido no churn)
--   FP cost = monthly_charges × 2 × 0.20   (2 meses de oferta de retenção com 20% de desconto)
--
-- No dataset IBM Telco, cltv varia de ~R$1.400 a ~R$8.600.
-- O custo flat de R$2.000/FN era uma aproximação da mediana; o modo cltv usa o valor real.

INSERT INTO churn.cost_model_config (
    tenant_id,
    project_id,
    cost_model,
    fp_cost_months,
    fp_cost_discount,
    fn_cost_cltv_multiplier,
    notes
)
SELECT
    t.id,
    p.id,
    'cltv',
    2.0,
    0.20,
    1.0,
    'IBM Telco — custo real por cliente. FN = 100% do CLTV perdido. FP = 2 meses × 20% de desconto na mensalidade.'
FROM churn.tenants  t
JOIN churn.projects p ON p.tenant_id = t.id
WHERE t.slug = 'ibm-telco'
  AND p.slug = 'telco-churn-2018'
ON CONFLICT (tenant_id, project_id, cost_model) DO NOTHING;
