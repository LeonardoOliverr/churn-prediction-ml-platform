import { useState, useMemo } from 'react'
import {
  Icon, MetricCard, SectionCard, ChartArea, Bars, Donut,
  Sparkline, Table, Th, Td, Tr, KV, StatusBadge,
  fmt, sparkline,
} from '@/components/primitives'
import { useAuthStore } from '@/store/authStore'

// ── Constantes de negócio (dataset IBM Telco) ─────────────────────────────────
const TOTAL_CUSTOMERS   = 7_043
const CHURN_RATE        = 0.2653          // taxa real de churn IBM Telco
const AVG_MRR_CUSTOMER  = 64.76           // receita média mensal por cliente
const TOTAL_MRR         = Math.round(TOTAL_CUSTOMERS * AVG_MRR_CUSTOMER)

const HIGH_RISK_COUNT   = 487             // prob churn >= 0.70
const MED_RISK_COUNT    = 1_284           // prob churn 0.40–0.70
const LOW_RISK_COUNT    = TOTAL_CUSTOMERS - HIGH_RISK_COUNT - MED_RISK_COUNT

const HIGH_RISK_AVG_MRR = 78.4           // fibra óptica pesa mais → ARPU maior
const MED_RISK_AVG_MRR  = 68.2
const LOW_RISK_AVG_MRR  = 58.1

const HIGH_RISK_MRR = Math.round(HIGH_RISK_COUNT * HIGH_RISK_AVG_MRR)
const MED_RISK_MRR  = Math.round(MED_RISK_COUNT  * MED_RISK_AVG_MRR)
const TOTAL_AT_RISK_MRR = HIGH_RISK_MRR + MED_RISK_MRR

// ROI do modelo — baseado em 82% precisão, 28% taxa de intervenção bem-sucedida
const MODEL_PRECISION        = 0.82
const INTERVENTION_RATE      = 0.28
const MONTHLY_SAVED          = Math.round(HIGH_RISK_COUNT * MODEL_PRECISION * INTERVENTION_RATE * HIGH_RISK_AVG_MRR)
const ANNUAL_SAVED           = MONTHLY_SAVED * 12
const MODEL_COST_ANNUAL      = 18_000     // estimativa de custo: infra + engenharia
const MODEL_ROI_X            = +(ANNUAL_SAVED / MODEL_COST_ANNUAL).toFixed(1)

// Churn por segmento de contrato (IBM Telco real)
const SEGMENTS_CONTRACT = [
  { label: 'Mensal',   churn_rate: 0.428, customers: 3_875, mrr_at_risk: 52_400 },
  { label: '1 ano',    churn_rate: 0.113, customers: 1_473, mrr_at_risk: 11_900 },
  { label: '2 anos',   churn_rate: 0.028, customers: 1_695, mrr_at_risk:  3_200 },
]

// Churn por tipo de internet (IBM Telco real)
const SEGMENTS_INTERNET = [
  { label: 'Fibra óptica', churn_rate: 0.418, customers: 3_096, mrr_at_risk: 67_800 },
  { label: 'DSL',          churn_rate: 0.190, customers: 2_421, mrr_at_risk: 18_400 },
  { label: 'Sem internet', churn_rate: 0.074, customers: 1_526, mrr_at_risk:  5_900 },
]

// Principais clientes em risco
const AT_RISK_CUSTOMERS = [
  { id: '7590-VHVEG', tenure: 1,  contract: 'Mensal', internet: 'Fibra óptica', monthly: 99.65, prob: 0.923, risk: 'high'   },
  { id: '5575-GNVDE', tenure: 34, contract: 'Mensal', internet: 'Fibra óptica', monthly: 93.20, prob: 0.891, risk: 'high'   },
  { id: '3668-QPYBK', tenure: 2,  contract: 'Mensal', internet: 'Fibra óptica', monthly: 88.15, prob: 0.874, risk: 'high'   },
  { id: '7795-CFOCW', tenure: 8,  contract: 'Mensal', internet: 'DSL',          monthly: 71.50, prob: 0.812, risk: 'high'   },
  { id: '9237-HQITU', tenure: 5,  contract: 'Mensal', internet: 'Fibra óptica', monthly: 104.8, prob: 0.793, risk: 'high'   },
  { id: '9305-CDSKC', tenure: 22, contract: '1 ano',  internet: 'Fibra óptica', monthly: 85.35, prob: 0.751, risk: 'high'   },
  { id: '1452-KIOVK', tenure: 11, contract: 'Mensal', internet: 'Fibra óptica', monthly: 79.65, prob: 0.744, risk: 'high'   },
  { id: '6713-OKOMC', tenure: 3,  contract: 'Mensal', internet: 'DSL',          monthly: 61.40, prob: 0.698, risk: 'medium' },
  { id: '7892-POOKP', tenure: 18, contract: 'Mensal', internet: 'Fibra óptica', monthly: 95.10, prob: 0.681, risk: 'medium' },
  { id: '6388-TABGU', tenure: 7,  contract: 'Mensal', internet: 'DSL',          monthly: 59.90, prob: 0.665, risk: 'medium' },
]

// Tendência de receita em risco — 13 semanas (leve melhora após deploy do modelo)
function buildRevTrend() {
  const base = [145, 141, 138, 149, 152, 147, 139, 135, 132, 129, 127, 124, 121]
  return base.map(v => v * 1000 + (Math.sin(v * 0.3) * 4000))
}

const REV_TREND = buildRevTrend()

// Tendência de churn semanal (queda leve = modelo funcionando)
function buildChurnTrend() {
  return Array.from({ length: 13 }, (_, i) => 28.4 - i * 0.3 + Math.sin(i * 1.1) * 1.2)
}

type RangeOpt = '30d' | '90d' | 'ytd'

export function BusinessPage() {
  const { selectedTenantId, selectedProjectId, knownTenants, knownProjects } = useAuthStore()
  const [range, setRange] = useState<RangeOpt>('30d')
  const [segment, setSegment] = useState<'contrato' | 'internet'>('contrato')

  const tenant  = knownTenants.find(t => t.id === selectedTenantId)
  const project = knownProjects.find(p => p.id === selectedProjectId)

  const churnTrend  = useMemo(() => buildChurnTrend(), [])
  const scoreTrend  = useMemo(() => sparkline(17, 13, 81, 4), [])
  const revenueBars = useMemo(() => REV_TREND, [])

  const segRows = segment === 'contrato' ? SEGMENTS_CONTRACT : SEGMENTS_INTERNET
  const maxMrrRisk = Math.max(...segRows.map(s => s.mrr_at_risk))

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>

      {/* Cabeçalho */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div style={{ fontSize: 14, color: 'var(--fg-1)', fontWeight: 500 }}>Dashboard executivo</div>
          <div style={{ fontSize: 12, color: 'var(--fg-3)', marginTop: 2 }}>
            {tenant?.name ?? 'IBM Telco'} · {project?.name ?? 'telco-churn-2018'} · visão estratégica
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Seletor de período */}
          <div style={{ display: 'flex', gap: 0, padding: 2, background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 5 }}>
            {(['30d', '90d', 'ytd'] as RangeOpt[]).map(r => (
              <button key={r} onClick={() => setRange(r)} className="btn btn-sm" style={{
                background:  range === r ? 'var(--bg-3)' : 'transparent',
                borderColor: range === r ? 'var(--border-2)' : 'transparent',
                color:       range === r ? 'var(--fg-1)' : 'var(--fg-3)',
                minWidth: 40, justifyContent: 'center',
              }}>{r}</button>
            ))}
          </div>
          <button className="btn"><Icon name="download" size={12}/> Exportar</button>
        </div>
      </div>

      {/* KPIs principais */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--gap-grid)' }}>
        <MetricCard
          label="Receita em risco"
          value={`$${fmt.compact(TOTAL_AT_RISK_MRR)}`}
          unit="/mês"
          hint={`${HIGH_RISK_COUNT + MED_RISK_COUNT} clientes`}
          accent="var(--warn)"
          sparkData={sparkline(3, 13, TOTAL_AT_RISK_MRR / 1000, 8)}
          sparkColor="var(--warn-fg)"
        />
        <MetricCard
          label="Churn prevenido"
          value={`$${fmt.compact(MONTHLY_SAVED)}`}
          unit="/mês"
          hint={`$${fmt.compact(ANNUAL_SAVED)}/ano`}
          accent="var(--ok)"
          sparkData={sparkline(9, 13, MONTHLY_SAVED / 1000, 5)}
          sparkColor="var(--ok-fg)"
        />
        <MetricCard
          label="Taxa de retenção"
          value={`${((1 - CHURN_RATE) * 100).toFixed(1)}%`}
          hint={`${(CHURN_RATE * 100).toFixed(1)}% de churn`}
          sparkData={churnTrend.map(v => 100 - v)}
          sparkColor="var(--accent-fg)"
        />
        <MetricCard
          label="ROI do modelo"
          value={`${MODEL_ROI_X}×`}
          hint={`$${fmt.compact(ANNUAL_SAVED)} poupado / $${fmt.compact(MODEL_COST_ANNUAL)} custo`}
          sparkData={scoreTrend}
          sparkColor="var(--ok-fg)"
        />
      </div>

      {/* Tendência semanal de receita em risco */}
      <SectionCard
        title="Receita em risco · tendência semanal"
        pad={false}
        action={
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', fontSize: 11 }}>
            <span style={{ display: 'flex', gap: 5, alignItems: 'center', color: 'var(--fg-3)' }}>
              <span style={{ width: 10, height: 2, background: 'var(--warn-fg)', borderRadius: 999, display: 'inline-block' }}/>
              Em risco
            </span>
            <span style={{ display: 'flex', gap: 5, alignItems: 'center', color: 'var(--fg-3)' }}>
              <span style={{ width: 10, height: 2, background: 'var(--ok-fg)', borderRadius: 999, display: 'inline-block' }}/>
              Prevenido
            </span>
            <span className="num" style={{ color: 'var(--fg-4)' }}>13s · snapshots semanais</span>
          </div>
        }
      >
        <div style={{ padding: '14px 16px 0', display: 'flex', gap: 24, marginBottom: 8 }}>
          <div>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Pico em risco</div>
            <div className="num" style={{ fontSize: 16, color: 'var(--warn-fg)', fontWeight: 500 }}>${fmt.compact(Math.max(...revenueBars))}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Atual</div>
            <div className="num" style={{ fontSize: 16, color: 'var(--fg-1)', fontWeight: 500 }}>${fmt.compact(revenueBars[revenueBars.length - 1])}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Tendência 13s</div>
            <div className="num" style={{ fontSize: 16, color: 'var(--ok-fg)', fontWeight: 500 }}>
              ↓ {(((revenueBars[0] - revenueBars[revenueBars.length - 1]) / revenueBars[0]) * 100).toFixed(1)}%
            </div>
          </div>
        </div>
        <div style={{ padding: '0 16px 14px' }}>
          <ChartArea data={revenueBars} height={110} color="var(--warn-fg)"/>
        </div>
      </SectionCard>

      {/* Segmentos + Impacto financeiro */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>

        {/* Churn por segmento */}
        <SectionCard
          title="Risco de churn por segmento"
          pad={false}
          action={
            <div style={{ display: 'flex', gap: 0, padding: 2, background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 4 }}>
              {(['contrato', 'internet'] as const).map(s => (
                <button key={s} onClick={() => setSegment(s)} className="btn btn-sm" style={{
                  background:  segment === s ? 'var(--bg-3)' : 'transparent',
                  borderColor: segment === s ? 'var(--border-2)' : 'transparent',
                  color:       segment === s ? 'var(--fg-1)' : 'var(--fg-3)',
                  textTransform: 'capitalize',
                }}>{s}</button>
              ))}
            </div>
          }
        >
          <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {segRows.map(s => (
              <div key={s.label}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, color: 'var(--fg-1)' }}>{s.label}</span>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <span className="num" style={{ fontSize: 12, color: s.churn_rate > 0.3 ? 'var(--crit-fg)' : s.churn_rate > 0.1 ? 'var(--warn-fg)' : 'var(--ok-fg)' }}>
                      {(s.churn_rate * 100).toFixed(1)}% churn
                    </span>
                    <span className="num" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
                      ${fmt.compact(s.mrr_at_risk)}/mês em risco
                    </span>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, alignItems: 'center' }}>
                  <div style={{ position: 'relative', height: 8, background: 'var(--bg-3)', borderRadius: 999 }}>
                    <div style={{
                      position: 'absolute', left: 0, top: 0, height: '100%',
                      width: `${s.churn_rate * 100}%`,
                      background: s.churn_rate > 0.3 ? 'var(--crit-fg)' : s.churn_rate > 0.1 ? 'var(--warn-fg)' : 'var(--ok-fg)',
                      borderRadius: 999, maxWidth: '100%',
                    }}/>
                    <div style={{
                      position: 'absolute', left: 0, top: 0, height: '100%',
                      width: `${(s.mrr_at_risk / maxMrrRisk) * 100}%`,
                      background: 'transparent',
                      borderRadius: 999,
                    }}/>
                  </div>
                  <span className="num" style={{ fontSize: 11, color: 'var(--fg-4)', width: 70, textAlign: 'right' }}>
                    {fmt.num(s.customers)} clientes
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Gráfico de volume */}
          <div style={{ padding: '10px 16px 14px', borderTop: '1px solid var(--divider)' }}>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
              MRR em risco · volume relativo
            </div>
            <Bars data={segRows.map(s => s.mrr_at_risk / 1000)} height={32} color="var(--warn-fg)" gap={4}/>
          </div>
        </SectionCard>

        {/* Impacto financeiro do modelo */}
        <SectionCard title="Impacto financeiro do modelo" pad={false}>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Donut — prevenido vs em risco */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <Donut
                value={Math.round((MONTHLY_SAVED / TOTAL_AT_RISK_MRR) * 100)}
                size={72} stroke={8}
                color="var(--ok-fg)" track="var(--bg-3)"
                label={`${Math.round((MONTHLY_SAVED / TOTAL_AT_RISK_MRR) * 100)}%`}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: 'var(--fg-1)', fontWeight: 500 }}>
                  Cobertura de mitigação
                </div>
                <div style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 4 }}>
                  ${fmt.compact(MONTHLY_SAVED)}/mês prevenido de ${fmt.compact(TOTAL_AT_RISK_MRR)}/mês de risco total
                </div>
              </div>
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--divider)', margin: 0 }}/>

            <KV items={[
              ['Precisão do modelo',      `${(MODEL_PRECISION * 100).toFixed(0)}%`],
              ['Taxa de intervenção',     `${(INTERVENTION_RATE * 100).toFixed(0)}%`],
              ['MRR salvo/mês',           `$${fmt.compact(MONTHLY_SAVED)}`],
              ['MRR salvo/ano',           `$${fmt.compact(ANNUAL_SAVED)}`],
              ['Custo infra do modelo/ano', `$${fmt.compact(MODEL_COST_ANNUAL)}`],
              ['Benefício líquido anual', `$${fmt.compact(ANNUAL_SAVED - MODEL_COST_ANNUAL)}`],
              ['ROI',                     `${MODEL_ROI_X}×`],
            ]}/>

            <div style={{ padding: '10px 12px', background: 'var(--ok-soft)', border: '1px solid var(--ok-line)', borderRadius: 4, fontSize: 12, color: 'var(--ok-fg)', display: 'flex', gap: 8 }}>
              <Icon name="trend-up" size={13} style={{ flexShrink: 0, marginTop: 1 }}/>
              <span>O modelo champion gera <strong>${fmt.compact(ANNUAL_SAVED - MODEL_COST_ANNUAL)}</strong> de benefício líquido anual vs. baseline sem modelo.</span>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Resumo por faixa de risco */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--gap-grid)' }}>
        <RiskTierCard
          tier="Alto risco"
          count={HIGH_RISK_COUNT}
          mrr={HIGH_RISK_MRR}
          avgMrr={HIGH_RISK_AVG_MRR}
          pctOfTotal={(HIGH_RISK_COUNT / TOTAL_CUSTOMERS) * 100}
          color="var(--crit-fg)"
          softColor="var(--crit-soft)"
          lineColor="var(--crit-line)"
          spark={sparkline(3, 13, HIGH_RISK_MRR / 1000, 5)}
          threshold="≥ 0.70"
        />
        <RiskTierCard
          tier="Médio risco"
          count={MED_RISK_COUNT}
          mrr={MED_RISK_MRR}
          avgMrr={MED_RISK_AVG_MRR}
          pctOfTotal={(MED_RISK_COUNT / TOTAL_CUSTOMERS) * 100}
          color="var(--warn-fg)"
          softColor="var(--warn-soft)"
          lineColor="var(--warn-line)"
          spark={sparkline(11, 13, MED_RISK_MRR / 1000, 8)}
          threshold="0.40 – 0.70"
        />
        <RiskTierCard
          tier="Baixo risco"
          count={LOW_RISK_COUNT}
          mrr={Math.round(LOW_RISK_COUNT * LOW_RISK_AVG_MRR)}
          avgMrr={LOW_RISK_AVG_MRR}
          pctOfTotal={(LOW_RISK_COUNT / TOTAL_CUSTOMERS) * 100}
          color="var(--ok-fg)"
          softColor="var(--ok-soft)"
          lineColor="var(--ok-line)"
          spark={sparkline(23, 13, (LOW_RISK_COUNT * LOW_RISK_AVG_MRR) / 1000, 12)}
          threshold="< 0.40"
        />
      </div>

      {/* Tabela de principais clientes em risco */}
      <SectionCard
        title="Principais clientes em risco · por impacto na receita"
        pad={false}
        action={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: 'var(--fg-4)' }}>ordenado por receita mensal</span>
            <button className="btn btn-sm"><Icon name="download" size={11}/> Exportar</button>
          </div>
        }
      >
        <Table>
          <thead>
            <tr>
              <Th>ID do cliente</Th>
              <Th align="right">Tempo</Th>
              <Th>Contrato</Th>
              <Th>Internet</Th>
              <Th align="right">MRR mensal</Th>
              <Th align="right">Impacto 12m</Th>
              <Th align="right">Prob. churn</Th>
              <Th align="right">Risco</Th>
            </tr>
          </thead>
          <tbody>
            {AT_RISK_CUSTOMERS.map(c => (
              <Tr key={c.id}>
                <Td mono style={{ color: 'var(--fg-1)' }}>{c.id}</Td>
                <Td mono align="right" style={{ color: 'var(--fg-3)' }}>{c.tenure}m</Td>
                <Td style={{ fontSize: 12, color: 'var(--fg-2)' }}>{c.contract}</Td>
                <Td style={{ fontSize: 12, color: 'var(--fg-3)' }}>{c.internet}</Td>
                <Td mono align="right" style={{ color: 'var(--fg-1)' }}>${c.monthly.toFixed(2)}</Td>
                <Td mono align="right" style={{ color: 'var(--warn-fg)', fontWeight: 500 }}>${fmt.compact(c.monthly * 12)}</Td>
                <Td mono align="right" style={{ color: c.prob >= 0.7 ? 'var(--crit-fg)' : 'var(--warn-fg)' }}>
                  {(c.prob * 100).toFixed(1)}%
                </Td>
                <Td align="right">
                  <StatusBadge
                    status={c.risk === 'high' ? 'critical' : 'warning'}
                    label={c.risk === 'high' ? 'ALTO' : 'MÉDIO'}
                    size="xs"
                  />
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
        <div style={{ padding: '10px 16px', borderTop: '1px solid var(--divider)', display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--fg-4)' }}>
          <span>Exibindo top 10 de {fmt.num(HIGH_RISK_COUNT + MED_RISK_COUNT)} clientes em risco</span>
          <span className="num">Exposição total 12m: <span style={{ color: 'var(--warn-fg)' }}>${fmt.compact(AT_RISK_CUSTOMERS.reduce((a, c) => a + c.monthly * 12, 0))}</span></span>
        </div>
      </SectionCard>

    </div>
  )
}

/* ── RiskTierCard ── */
function RiskTierCard({ tier, count, mrr, avgMrr, pctOfTotal, color, softColor, lineColor, spark, threshold }: {
  tier: string; count: number; mrr: number; avgMrr: number
  pctOfTotal: number; color: string; softColor: string; lineColor: string
  spark: number[]; threshold: string
}) {
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--divider)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: `color-mix(in oklab, ${softColor} 40%, transparent)` }}>
        <div style={{ fontSize: 12, color, fontWeight: 500 }}>{tier}</div>
        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 6px', borderRadius: 3, background: softColor, color, border: `1px solid ${lineColor}` }}>{threshold}</span>
      </div>
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div className="num" style={{ fontSize: 28, fontWeight: 500, color, letterSpacing: '-0.02em', lineHeight: 1 }}>
              {fmt.num(count)}
            </div>
            <div style={{ fontSize: 11, color: 'var(--fg-4)', marginTop: 4 }}>
              {pctOfTotal.toFixed(1)}% dos clientes
            </div>
          </div>
          <Sparkline data={spark} width={80} height={32} color={color} fill={false} strokeWidth={1.2}/>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
          <div>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>MRR em risco</div>
            <div className="num" style={{ color: 'var(--fg-1)', marginTop: 2 }}>${fmt.compact(mrr)}/mês</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>ARPU médio</div>
            <div className="num" style={{ color: 'var(--fg-1)', marginTop: 2 }}>${avgMrr.toFixed(2)}</div>
          </div>
        </div>
        {/* Barra de risco proporcional */}
        <div style={{ height: 4, background: 'var(--bg-3)', borderRadius: 999 }}>
          <div style={{ height: '100%', width: `${pctOfTotal}%`, background: color, borderRadius: 999, maxWidth: '100%' }}/>
        </div>
      </div>
    </div>
  )
}
