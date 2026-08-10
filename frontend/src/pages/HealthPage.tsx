import { useQuery } from '@tanstack/react-query'
import {
  Icon, StatusBadge, SectionCard, Sparkline,
  Table, Th, Td, Tr, sparkline,
} from '@/components/primitives'
import { fetchHealth, fetchHealthReady } from '@/services/health'

const SERVICES = [
  { id: 'control-plane', name: 'Control plane',  p99: 18 },
  { id: 'feature-store', name: 'Feature store',  p99: 22 },
  { id: 'registry',      name: 'Model registry', p99: 11 },
  { id: 'audit',         name: 'Audit logger',   p99: 38 },
  { id: 'gateway',       name: 'API gateway',    p99: 9  },
  { id: 'queue',         name: 'Async queue',    p99: 7  },
]

const ENDPOINTS = [
  { id: 'ep1', path: '/predict',       model: 'rf-churn@v3', rps: 42,  p50: 14, p95: 38,  p99: 72,  err: 0.0008 },
  { id: 'ep2', path: '/predict/batch', model: 'rf-churn@v3', rps: 6,   p50: 88, p95: 210, p99: 340, err: 0.0021 },
  { id: 'ep3', path: '/health',        model: '—',           rps: 120, p50: 2,  p95: 6,   p99: 11,  err: 0.0000 },
  { id: 'ep4', path: '/health/ready',  model: '—',           rps: 60,  p50: 3,  p95: 8,   p99: 14,  err: 0.0000 },
  { id: 'ep5', path: '/predictions',   model: '—',           rps: 18,  p50: 9,  p95: 24,  p99: 48,  err: 0.0002 },
]

const ALERTS = [
  { sev: 'warning', title: 'p99 latency above SLO',    endpoint: '/predict/batch', since: '12m' },
  { sev: 'info',    title: 'Auto-scaled replica 2→3',  endpoint: '/predict',       since: '32m' },
]

export function HealthPage() {
  const { data: health,      isLoading: hLoad } = useQuery({ queryKey: ['health'],       queryFn: fetchHealth,      refetchInterval: 15_000 })
  const { data: healthReady, isLoading: rLoad  } = useQuery({ queryKey: ['health-ready'], queryFn: fetchHealthReady, refetchInterval: 15_000 })

  const apiStatus  = health?.status === 'ok' ? 'healthy' : health ? 'degraded' : 'unknown'
  const dbStatus   = healthReady?.checks.database.status === 'ok' ? 'healthy' : healthReady ? 'degraded' : 'unknown'
  const mlflowStat = healthReady?.checks.mlflow.status   === 'ok' ? 'healthy' : healthReady ? 'degraded' : 'unknown'

  const services = SERVICES.map(s => {
    let status = 'healthy'
    if (s.id === 'control-plane') status = apiStatus
    if (s.id === 'registry')      status = mlflowStat
    if (s.id === 'feature-store') status = dbStatus
    return { ...s, status, region: 'us-east-1' }
  })

  const slo = ENDPOINTS.map(e => ({ ep: e, target: 99.9, achieved: 99.94 - e.err * 100 }))

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 14, color: 'var(--fg-1)', fontWeight: 500 }}>Platform health</div>
          <div style={{ fontSize: 12, color: 'var(--fg-3)', marginTop: 2 }}>
            {hLoad || rLoad ? 'Loading…' : (
              <>API <span className="mono" style={{ color: apiStatus === 'healthy' ? 'var(--ok-fg)' : 'var(--crit-fg)' }}>{health?.status ?? '—'}</span>
              {' · '}DB <span className="mono" style={{ color: dbStatus === 'healthy' ? 'var(--ok-fg)' : 'var(--crit-fg)' }}>{healthReady?.checks.database.status ?? '—'}</span>
              {' · '}MLflow <span className="mono" style={{ color: mlflowStat === 'healthy' ? 'var(--ok-fg)' : 'var(--crit-fg)' }}>{healthReady?.checks.mlflow.status ?? '—'}</span></>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn"><Icon name="history" size={12}/> Incidents</button>
          <button className="btn"><Icon name="external" size={12}/> Status page</button>
        </div>
      </div>

      {/* Service grid */}
      <SectionCard title="Services · current region" pad={false}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' }}>
          {services.map((s, i) => (
            <div key={s.id} style={{
              padding: '14px 16px',
              borderRight:  (i + 1) % 3 !== 0 ? '1px solid var(--divider)' : 'none',
              borderBottom: i < 3               ? '1px solid var(--divider)' : 'none',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <div style={{ position: 'relative', width: 10, height: 10, flexShrink: 0 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: 999, display: 'block',
                  background: s.status === 'healthy' ? 'var(--ok)' : s.status === 'degraded' ? 'var(--warn)' : 'var(--bg-3)',
                  boxShadow:  s.status === 'healthy' ? '0 0 8px var(--ok)' : 'none',
                }}/>
                {s.status === 'healthy' && <span className="blip" style={{ color: 'var(--ok)' }}/>}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, color: 'var(--fg-1)' }}>{s.name}</span>
                  <StatusBadge status={s.status} size="xs"/>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--fg-4)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                  <span>{s.region}</span>
                  <span>p99 {s.p99}ms</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Endpoints table */}
      <SectionCard title="Endpoints" pad={false}
        action={<span style={{ fontSize: 11, color: 'var(--fg-3)' }}>{ENDPOINTS.length} endpoints · 1m sample</span>}
      >
        <Table>
          <thead>
            <tr>
              <Th w={32}></Th>
              <Th>Endpoint</Th>
              <Th>Model</Th>
              <Th>Region</Th>
              <Th align="right">RPS</Th>
              <Th align="right">p50</Th>
              <Th align="right">p95</Th>
              <Th align="right">p99</Th>
              <Th align="right">Errors</Th>
              <Th>Last 60m</Th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINTS.map(e => {
              const sp   = sparkline(e.id.charCodeAt(2) * 5, 30, e.rps, e.rps * 0.3)
              const tone = e.err < 0.002 ? 'ok' : 'warn'
              return (
                <Tr key={e.id}>
                  <Td>
                    <span className="pulse-dot" style={{
                      display: 'inline-block', width: 8, height: 8, borderRadius: 999,
                      background: tone === 'ok' ? 'var(--ok)' : 'var(--warn)',
                      boxShadow:  tone === 'ok' ? '0 0 6px var(--ok)' : 'none',
                    }}/>
                  </Td>
                  <Td mono><span style={{ color: 'var(--fg-1)' }}>{e.path}</span></Td>
                  <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{e.model}</Td>
                  <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>us-east-1</Td>
                  <Td mono align="right">{e.rps}</Td>
                  <Td mono align="right" style={{ color: 'var(--fg-2)' }}>{e.p50}ms</Td>
                  <Td mono align="right" style={{ color: 'var(--fg-2)' }}>{e.p95}ms</Td>
                  <Td mono align="right" style={{ color: e.p99 > 200 ? 'var(--warn-fg)' : 'var(--fg-2)' }}>{e.p99}ms</Td>
                  <Td mono align="right" style={{ color: e.err > 0.002 ? 'var(--warn-fg)' : 'var(--fg-3)' }}>{(e.err * 100).toFixed(3)}%</Td>
                  <Td>
                    <Sparkline data={sp} width={120} height={20} strokeWidth={1}
                      color={tone === 'ok' ? 'var(--ok-fg)' : 'var(--warn-fg)'} fill={false}/>
                  </Td>
                </Tr>
              )
            })}
          </tbody>
        </Table>
      </SectionCard>

      {/* SLO + Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>
        <SectionCard title="SLO budget · 30d" pad={false}>
          <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {slo.map(s => (
              <div key={s.ep.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span className="mono" style={{ fontSize: 12, color: 'var(--fg-1)' }}>{s.ep.path}</span>
                  <span style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
                    <span className="num" style={{ fontSize: 11, color: 'var(--fg-3)' }}>target {s.target.toFixed(2)}%</span>
                    <span className="num" style={{ fontSize: 12, color: s.achieved >= s.target ? 'var(--ok-fg)' : 'var(--warn-fg)' }}>{s.achieved.toFixed(3)}%</span>
                  </span>
                </div>
                <div style={{ position: 'relative', height: 6, background: 'var(--bg-3)', borderRadius: 999 }}>
                  <div style={{ position: 'absolute', left: 0, height: '100%', width: `${s.achieved}%`, background: 'var(--ok-fg)', borderRadius: 999 }}/>
                  <div style={{ position: 'absolute', left: `${s.target}%`, top: -3, width: 2, height: 12, background: 'var(--fg-2)' }}/>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Open alerts" pad={false}>
          <div>
            {ALERTS.map((a, i) => (
              <div key={i} style={{
                padding: '12px 14px',
                borderBottom: i < ALERTS.length - 1 ? '1px solid var(--divider)' : 'none',
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}>
                <Icon name={a.sev === 'warning' ? 'alert' : 'info'} size={13}
                  style={{ color: a.sev === 'warning' ? 'var(--warn-fg)' : 'var(--accent-fg)', marginTop: 2 }}/>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: 'var(--fg-1)' }}>{a.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-4)', marginTop: 2 }}>
                    <span className="mono">{a.endpoint}</span> · firing {a.since}
                  </div>
                </div>
                <button className="btn btn-sm">Ack</button>
              </div>
            ))}
            {/* Real latency from /health/ready */}
            {healthReady && (
              <>
                <div style={{ padding: '10px 14px', borderTop: '1px solid var(--divider)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                  <span style={{ color: 'var(--fg-4)' }}>DB latency</span>
                  <span className="num" style={{ color: 'var(--fg-2)' }}>{healthReady.checks.database.latency_ms}ms</span>
                </div>
                <div style={{ padding: '0 14px 10px', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                  <span style={{ color: 'var(--fg-4)' }}>MLflow latency</span>
                  <span className="num" style={{ color: 'var(--fg-2)' }}>{healthReady.checks.mlflow.latency_ms}ms</span>
                </div>
              </>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
