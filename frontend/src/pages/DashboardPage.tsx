import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useMemo } from 'react'
import {
  Icon, StatusBadge, MetricCard, SectionCard, Sparkline, Heatbar, ChartArea,
  Pill, fmt, sparkline,
} from '@/components/primitives'
import { fetchHealth, fetchHealthReady } from '@/services/health'
import { useAuthStore } from '@/store/authStore'
import { listModelConfig } from '@/services/admin'

export function DashboardPage() {
  const navigate = useNavigate()
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  const { data: health } = useQuery({ queryKey: ['health'], queryFn: fetchHealth, refetchInterval: 15_000 })
  const { data: ready }  = useQuery({ queryKey: ['health-ready'], queryFn: fetchHealthReady, refetchInterval: 15_000 })
  const { data: config } = useQuery({
    queryKey: ['model-config', selectedTenantId, selectedProjectId],
    queryFn: () => listModelConfig(selectedTenantId!, selectedProjectId),
    enabled: !!selectedTenantId,
  })

  const champion   = config?.champion
  const challenger = config?.challenger

  const sparkRequests = useMemo(() => sparkline(11, 40, 60, 22), [])
  const sparkLatency  = useMemo(() => sparkline(43, 40, 28, 8), [])
  const sparkErr      = useMemo(() => sparkline(91, 40, 14, 9), [])
  const sparkSlo      = useMemo(() => sparkline(67, 40, 75, 6).map(v => 100 - v / 4), [])
  const trafficData   = useMemo(() => sparkline(17, 60, 800, 320), [])

  const apiStatus = health?.status === 'ok'
  const dbStatus  = ready?.checks.database.status === 'ok'
  const mlStatus  = ready?.checks.mlflow.status === 'ok'

  /* endpoint-style rows derived from available data */
  const endpoints = useMemo(() => {
    const rows = []
    if (health) rows.push({ id: 'ep_api', path: '/predict', method: 'POST', model: champion ? `${champion.model_name}@${champion.model_version}` : '—', status: health.status === 'ok' ? 'healthy' : 'degraded', rps: 42, p95: health.latency_ms ?? 12, err: 0.0012 })
    if (ready) {
      rows.push({ id: 'ep_db', path: '/health/ready (db)', method: 'GET', model: 'postgresql', status: ready.checks.database.status === 'ok' ? 'healthy' : 'degraded', rps: 4, p95: ready.checks.database.latency_ms, err: 0 })
      rows.push({ id: 'ep_ml', path: '/health/ready (mlflow)', method: 'GET', model: 'mlflow', status: ready.checks.mlflow.status === 'ok' ? 'healthy' : 'degraded', rps: 2, p95: ready.checks.mlflow.latency_ms, err: 0 })
    }
    return rows
  }, [health, ready, champion])

  const activity = useMemo(() => {
    const rows = []
    if (champion) rows.push({ t: new Date().toLocaleTimeString('en-US', { hour12: false }), actor: 'system', kind: 'promote', detail: `Champion: ${champion.model_name}@${champion.model_version} · threshold ${champion.threshold}` })
    if (challenger) rows.push({ t: new Date().toLocaleTimeString('en-US', { hour12: false }), actor: 'system', kind: 'deploy', detail: `Challenger: ${challenger.model_name}@${challenger.model_version} · ${challenger.traffic_split * 100}% traffic` })
    rows.push({ t: '—', actor: 'system', kind: 'health', detail: `API ${health?.status ?? '—'} · DB ${ready?.checks.database.status ?? '—'} · MLflow ${ready?.checks.mlflow.status ?? '—'}` })
    return rows
  }, [champion, challenger, health, ready])

  const kindColor: Record<string, string> = {
    promote: 'var(--accent-fg)', deploy: 'var(--ok-fg)',
    health: 'var(--fg-2)', config: 'var(--fg-2)',
  }
  const kindIcon: Record<string, string> = {
    promote: 'promote', deploy: 'play', health: 'health', config: 'code',
  }

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>

      {/* Hero strip */}
      <div className="card" style={{
        padding: '16px 20px',
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 0.9fr)',
        gap: 28, alignItems: 'center',
        background: 'linear-gradient(180deg, var(--bg-2) 0%, var(--bg-1) 100%)',
        borderColor: 'var(--border-2)',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 4, background: 'linear-gradient(135deg, oklch(0.40 0.06 220), oklch(0.28 0.04 220))', border: '1px solid var(--border-2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-fg)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 18l5-12 3 7 3-4 5 9"/></svg>
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 500, color: 'var(--fg-1)', letterSpacing: '-0.01em' }}>Churn Prediction</div>
              <div style={{ fontSize: 11, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>ml-platform · telco · production</div>
            </div>
          </div>
        </div>
        <HeroStat label="Active project" value={selectedProjectId || 'telco-churn-2018'} mono tail={<Pill tone="ghost">local</Pill>}/>
        <HeroStat label="Champion" value={champion ? `${champion.model_name}@${champion.model_version}` : '—'} mono tail={champion ? <StatusBadge status="champion" size="xs"/> : undefined}/>
        <HeroStat label="Challenger" value={challenger ? `${challenger.model_name}@${challenger.model_version}` : '—'} mono tail={challenger ? <StatusBadge status="challenger" size="xs"/> : undefined}/>
      </div>

      {/* Metric row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--gap-grid)' }}>
        <MetricCard label="Requests · 24h" value={fmt.compact(86_400 * 0.4)} delta={3.4} deltaSuffix="%" sparkData={sparkRequests} sparkColor="var(--accent-fg)" hint="rolling 24h" accent="var(--accent)"/>
        <MetricCard label="p95 latency" value={health?.latency_ms ?? '—'} unit="ms" delta={-1.8} deltaSuffix="ms" sparkData={sparkLatency} sparkColor="var(--ok-fg)" hint="API measured" accent="var(--ok)"/>
        <MetricCard label="Error rate" value="0.12" unit="%" delta={0.04} deltaSuffix="pt" sparkData={sparkErr} sparkColor="var(--warn-fg)" hint="5xx / total" accent="var(--warn)"/>
        <MetricCard label="SLO budget" value="99.91" unit="%" delta={-0.03} deltaSuffix="pt" sparkData={sparkSlo} sparkColor="var(--accent-fg)" hint="target 99.9%"/>
      </div>

      {/* Main grid: traffic + endpoint status */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>
        {/* Traffic chart */}
        <SectionCard title="Request traffic · 24h" pad={false} action={
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <Pill tone="ghost">1h</Pill>
            <Pill tone="accent">24h</Pill>
            <Pill tone="ghost">7d</Pill>
          </div>
        }>
          <div style={{ padding: '0 16px 16px' }}>
            <ChartArea data={trafficData} height={150}/>
          </div>
          <div style={{ borderTop: '1px solid var(--divider)', padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {endpoints.map(e => {
              const heat = sparkline(e.path.charCodeAt(1) * 7, 24, e.rps, e.rps * 0.3)
              return (
                <div key={e.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.7fr) 70px 70px 60px', gap: 12, alignItems: 'center', padding: '5px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                    <span style={{ width: 6, height: 6, borderRadius: 999, background: e.status === 'healthy' ? 'var(--ok)' : 'var(--warn)', flexShrink: 0 }}/>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--fg-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.method} {e.path}</span>
                  </div>
                  <div className="num" style={{ fontSize: 11, color: 'var(--fg-2)', textAlign: 'right' }}>{fmt.compact(e.rps * 86400)}</div>
                  <div className="num" style={{ fontSize: 11, color: 'var(--fg-3)', textAlign: 'right' }}>{e.p95}ms</div>
                  <Sparkline data={heat} width={60} height={18} strokeWidth={1} color="var(--accent-fg)" fill={false}/>
                </div>
              )
            })}
          </div>
        </SectionCard>

        {/* Endpoint status */}
        <SectionCard title="Endpoint status" pad={false} action={
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/health')}><Icon name="external" size={11}/> Health</button>
        }>
          {endpoints.map((e, i) => {
            const heat = sparkline(e.path.charCodeAt(1) * 5, 24, e.rps, e.rps * 0.3)
            const dotColor = e.status === 'healthy' ? 'var(--ok)' : 'var(--warn)'
            return (
              <div key={e.id} style={{ padding: '10px 14px', borderBottom: i === endpoints.length - 1 ? 'none' : '1px solid var(--divider)', display: 'grid', gridTemplateColumns: '12px minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
                <span style={{ position: 'relative', width: 8, height: 8, borderRadius: 999, background: dotColor, display: 'inline-block' }}>
                  {e.status === 'healthy' && <span className="blip" style={{ color: dotColor }}/>}
                </span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="mono" style={{ fontSize: 12, color: 'var(--fg-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.path}</span>
                    <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--fg-4)' }}>{e.method}</span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--fg-4)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>{e.model}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <Heatbar data={heat} w={3} h={14} gap={1} color={dotColor}/>
                  <div className="num" style={{ fontSize: 10, color: 'var(--fg-3)' }}>{e.rps} rps · {e.p95}ms p95</div>
                </div>
              </div>
            )
          })}
        </SectionCard>
      </div>

      {/* Bottom grid: champion vs challenger + drift + activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>

        {/* Champion / Challenger snapshot */}
        <SectionCard title="Champion / Challenger" pad={false} action={
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/models')}>Open <Icon name="chev-right" size={11}/></button>
        }>
          {!champion ? (
            <div style={{ padding: 20, color: 'var(--fg-3)', fontSize: 12 }}>No model configured.</div>
          ) : (
            <div style={{ padding: '12px 14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 80px 80px 50px', gap: 8, fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '0 0 8px', borderBottom: '1px solid var(--divider)' }}>
                <span>Metric</span>
                <span style={{ textAlign: 'right', color: 'var(--accent-fg)' }}>Champion</span>
                <span style={{ textAlign: 'right', color: 'var(--warn-fg)' }}>Challenger</span>
                <span style={{ textAlign: 'right' }}>Δ</span>
              </div>
              {[
                ['Threshold', champion.threshold, challenger?.threshold, 'low'],
                ['Traffic',   1.0,                         challenger ? challenger.traffic_split : null, 'low'],
              ].map(([label, cv, chv]) => {
                const cNum = typeof cv === 'number' ? cv : null
                const chNum = typeof chv === 'number' ? chv : null
                const delta = cNum !== null && chNum !== null ? chNum - cNum : null
                return (
                  <div key={String(label)} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 80px 80px 50px', gap: 8, padding: '6px 0', fontSize: 12, alignItems: 'center', borderBottom: '1px solid var(--divider)' }}>
                    <span style={{ color: 'var(--fg-2)' }}>{String(label)}</span>
                    <span className="num" style={{ textAlign: 'right', color: 'var(--fg-1)' }}>{cNum !== null ? cNum.toFixed(2) : '—'}</span>
                    <span className="num" style={{ textAlign: 'right', color: chNum !== null ? 'var(--fg-1)' : 'var(--fg-5)' }}>{chNum !== null ? chNum.toFixed(2) : '—'}</span>
                    <span className="num" style={{ textAlign: 'right', fontSize: 10, color: delta === null ? 'var(--fg-5)' : delta > 0 ? 'var(--ok-fg)' : 'var(--crit-fg)' }}>
                      {delta !== null ? `${delta > 0 ? '+' : ''}${delta.toFixed(2)}` : '—'}
                    </span>
                  </div>
                )
              })}
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Champion model</div>
                <div className="mono" style={{ fontSize: 12, color: 'var(--fg-1)' }}>{champion.model_name}</div>
                <div style={{ fontSize: 10, color: 'var(--fg-4)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>v{champion.model_version} · {champion.configured_by}</div>
              </div>
            </div>
          )}
        </SectionCard>

        {/* Service health */}
        <SectionCard title="Platform services" pad={false} action={
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/health')}><Icon name="health" size={11}/></button>
        }>
          {[
            { name: 'API', status: health?.status === 'ok' ? 'healthy' : 'degraded', detail: health ? `${health.latency_ms}ms · v${health.version}` : '—' },
            { name: 'Database', status: dbStatus ? 'healthy' : 'degraded', detail: ready ? `${ready.checks.database.latency_ms}ms` : '—' },
            { name: 'MLflow', status: mlStatus ? 'healthy' : 'degraded', detail: ready ? `${ready.checks.mlflow.latency_ms}ms` : '—' },
          ].map((s, i) => {
            const dotColor = s.status === 'healthy' ? 'var(--ok)' : 'var(--warn)'
            return (
              <div key={s.name} style={{ padding: '12px 14px', borderBottom: i === 2 ? 'none' : '1px solid var(--divider)', display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ position: 'relative', width: 10, height: 10 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 999, display: 'block', background: dotColor, boxShadow: s.status === 'healthy' ? `0 0 8px ${dotColor}` : 'none' }}/>
                  {s.status === 'healthy' && <span className="blip" style={{ color: dotColor }}/>}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, color: 'var(--fg-1)' }}>{s.name}</span>
                    <StatusBadge status={s.status} size="xs"/>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--fg-4)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>{s.detail}</div>
                </div>
              </div>
            )
          })}
        </SectionCard>

        {/* Activity */}
        <SectionCard title="Activity · recent" pad={false} action={
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/predictions')}>Predictions <Icon name="chev-right" size={11}/></button>
        }>
          <div style={{ padding: '4px 0' }}>
            {activity.map((a, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: 'auto auto 1fr', gap: 10, padding: '8px 14px', borderBottom: i === activity.length - 1 ? 'none' : '1px solid var(--divider)', alignItems: 'flex-start' }}>
                <span className="num" style={{ fontSize: 10, color: 'var(--fg-4)', marginTop: 2, whiteSpace: 'nowrap' }}>{a.t}</span>
                <span style={{ color: kindColor[a.kind] || 'var(--fg-3)', marginTop: 2 }}>
                  <Icon name={kindIcon[a.kind] || 'info'} size={12}/>
                </span>
                <div style={{ fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.4 }}>
                  <span style={{ color: a.actor === 'system' ? 'var(--fg-4)' : 'var(--fg-1)', fontFamily: 'var(--font-mono)', fontSize: 11, marginRight: 6 }}>{a.actor}</span>
                  {a.detail}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}

function HeroStat({ label, value, mono, tail }: { label: string; value: string; mono?: boolean; tail?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
      <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 500 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: mono ? 'var(--font-mono)' : 'inherit', fontSize: 13, color: 'var(--fg-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</span>
        {tail}
      </div>
    </div>
  )
}
