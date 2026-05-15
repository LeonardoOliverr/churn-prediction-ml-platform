import { useState, useMemo } from 'react'
import {
  Icon, MetricCard, SectionCard, Bars, KV, CodeBlock,
  Table, Th, Td, Tr, fmt, sparkline,
} from '@/components/primitives'
import { usePredictions } from '@/hooks/usePredictions'
import type { PredictionRecord } from '@/types/api'

export function PredictionsPage() {
  const [page, setPage]     = useState(1)
  const pageSize            = 50
  const { data, isLoading } = usePredictions(page, pageSize)
  const [filters, setFilters] = useState({ decision: 'all', q: '' })
  const [selected, setSelected] = useState<PredictionRecord | null>(null)

  const items = data?.items ?? []

  const filtered = useMemo(() => items.filter(p => {
    if (filters.decision === 'positive' && !p.churn_pred) return false
    if (filters.decision === 'negative' &&  p.churn_pred) return false
    if (filters.q && !p.id.toLowerCase().includes(filters.q.toLowerCase()) && !p.customer_id.toLowerCase().includes(filters.q.toLowerCase())) return false
    return true
  }), [items, filters])

  const counts = useMemo(() => ({
    pos:  filtered.filter(p => p.churn_pred).length,
    slow: filtered.filter(p => (p.latency_ms ?? 0) > 80).length,
  }), [filtered])

  const histogram = useMemo(() => sparkline(filtered.length + 11, 64, 28, 16), [filtered.length])
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>
      {/* Top stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--gap-grid)' }}>
        <MetricCard label="Total predictions" value={fmt.num(data?.total ?? 0)} unit="rows" hint="all time"/>
        <MetricCard label="Positive (churn)" value={fmt.num(counts.pos)} unit="rows"
          hint={`${((counts.pos / Math.max(1, filtered.length)) * 100).toFixed(1)}%`} accent="var(--warn)"/>
        <MetricCard label="High latency" value={counts.slow} unit="rows"
          hint="> 80 ms" accent="var(--crit)"/>
        <MetricCard label="Showing" value={filtered.length} unit="rows"
          hint={`page ${page}`} sparkData={histogram} sparkColor="var(--accent-fg)"/>
      </div>

      {/* Filter bar */}
      <div className="card" style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <FilterField label="Decision">
          <SegmentedFilter value={filters.decision} onChange={v => setFilters(f => ({ ...f, decision: v }))}
            options={[['all','All'], ['positive','Positive'], ['negative','Negative']]}/>
        </FilterField>
        <div style={{ flex: 1 }}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px', width: 260,
          background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 4 }}>
          <Icon name="search" size={12} style={{ color: 'var(--fg-4)' }}/>
          <input className="mono" placeholder="prediction id / customer id"
            value={filters.q} onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
            style={{ background: 'transparent', border: 'none', outline: 'none',
              color: 'var(--fg-1)', fontSize: 11, width: '100%', fontFamily: 'var(--font-mono)' }}/>
        </div>
      </div>

      {/* Volume strip */}
      <div className="card" style={{ padding: '10px 14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Volume · current page</span>
          <span className="num" style={{ fontSize: 11, color: 'var(--fg-3)' }}>peak {Math.max(...histogram).toFixed(0)} pred/s (simulated)</span>
        </div>
        <Bars data={histogram} height={36} color="var(--accent-fg)" gap={1}/>
      </div>

      {/* Table + side panel */}
      <div style={{ display: 'grid', gridTemplateColumns: selected ? 'minmax(0, 1.6fr) minmax(0, 1fr)' : '1fr', gap: 'var(--gap-grid)' }}>
        <SectionCard title={`Predictions · ${filtered.length} rows`} pad={false}
          action={
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 10, color: 'var(--fg-4)' }}>auto-refresh</span>
              <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--ok)', boxShadow: '0 0 6px var(--ok)' }}/>
            </div>
          }
        >
          {isLoading && (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>Loading…</div>
          )}
          <div style={{ maxHeight: 'calc(100vh - 420px)', overflow: 'auto' }}>
            <Table>
              <thead>
                <tr>
                  <Th>Time UTC</Th>
                  <Th>Prediction ID</Th>
                  <Th>Customer</Th>
                  <Th align="right">Score</Th>
                  <Th align="right">Decision</Th>
                  <Th align="right">Threshold</Th>
                  <Th align="right">Latency</Th>
                  <Th w={20}></Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <Tr key={p.id} selected={selected?.id === p.id} onClick={() => setSelected(p)}>
                    <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{p.requested_at.slice(11, 19)}</Td>
                    <Td mono style={{ color: 'var(--fg-2)', fontSize: 11 }}>{p.id.slice(0, 13)}…</Td>
                    <Td mono style={{ color: 'var(--fg-1)', fontSize: 11 }}>{p.customer_id}</Td>
                    <Td mono align="right" style={{ color: p.churn_probability >= p.threshold_used ? 'var(--warn-fg)' : 'var(--fg-2)' }}>
                      {p.churn_probability.toFixed(4)}
                    </Td>
                    <Td align="right">
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 11, padding: '1px 6px', borderRadius: 2,
                        background:  p.churn_pred ? 'var(--warn-soft)' : 'transparent',
                        color:       p.churn_pred ? 'var(--warn-fg)' : 'var(--fg-2)',
                        border: `1px solid ${p.churn_pred ? 'var(--warn-line)' : 'transparent'}`,
                      }}>{p.churn_pred ? 'POSITIVE' : 'NEGATIVE'}</span>
                    </Td>
                    <Td mono align="right" style={{ color: 'var(--fg-3)' }}>{p.threshold_used.toFixed(2)}</Td>
                    <Td mono align="right" style={{ color: (p.latency_ms ?? 0) > 80 ? 'var(--warn-fg)' : 'var(--fg-3)' }}>
                      {p.latency_ms != null ? `${p.latency_ms}ms` : '—'}
                    </Td>
                    <Td><Icon name="chev-right" size={12} style={{ color: 'var(--fg-4)' }}/></Td>
                  </Tr>
                ))}
                {!isLoading && filtered.length === 0 && (
                  <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>No predictions found</td></tr>
                )}
              </tbody>
            </Table>
          </div>
          {/* Pagination */}
          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--divider)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <span className="num" style={{ fontSize: 11, color: 'var(--fg-3)' }}>
              {data?.total ?? 0} total · page {page} of {totalPages}
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button className="btn btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                <Icon name="chev-left" size={11}/> Prev
              </button>
              <button className="btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                Next <Icon name="chev-right" size={11}/>
              </button>
            </div>
          </div>
        </SectionCard>

        {selected && <PredictionDetail prediction={selected} onClose={() => setSelected(null)}/>}
      </div>
    </div>
  )
}

/* ── Sub-components ── */

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      {children}
    </div>
  )
}

function SegmentedFilter({ value, onChange, options }: {
  value: string; onChange: (v: string) => void
  options: [string, string][]
}) {
  return (
    <div style={{ display: 'flex', gap: 0, padding: 2, background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 4 }}>
      {options.map(([v, label]) => (
        <button key={v} onClick={() => onChange(v)} style={{
          padding: '3px 8px', background: value === v ? 'var(--bg-3)' : 'transparent',
          border: 'none', color: value === v ? 'var(--fg-1)' : 'var(--fg-3)',
          fontSize: 11, cursor: 'pointer', fontFamily: 'inherit', borderRadius: 3,
        }}>{label}</button>
      ))}
    </div>
  )
}

function DetailCell({ label, value, mono, tone }: { label: string; value: string; mono?: boolean; tone?: string }) {
  return (
    <div style={{ padding: '10px 12px', background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 4 }}>
      <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 14, color: tone ?? 'var(--fg-1)', marginTop: 2, fontFamily: mono ? 'var(--font-mono)' : 'inherit', fontVariantNumeric: mono ? 'tabular-nums' : 'normal' }}>{value}</div>
    </div>
  )
}

function PredictionDetail({ prediction: p, onClose }: { prediction: PredictionRecord; onClose: () => void }) {
  return (
    <SectionCard title={`Prediction · ${p.id.slice(0, 13)}…`} pad={false}
      action={<button className="btn btn-ghost btn-sm" onClick={onClose}><Icon name="x" size={12}/></button>}
    >
      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <DetailCell label="Decision" value={p.churn_pred ? 'POSITIVE' : 'NEGATIVE'} tone={p.churn_pred ? 'var(--warn-fg)' : 'var(--ok-fg)'}/>
          <DetailCell label="Score" value={p.churn_probability.toFixed(4)} mono/>
          <DetailCell label="Threshold" value={p.threshold_used.toFixed(2)} mono/>
          <DetailCell label="Latency" value={p.latency_ms != null ? `${p.latency_ms}ms` : '—'} mono/>
        </div>
        <hr className="hr"/>
        <KV mono items={[
          ['Prediction ID', p.id],
          ['Customer ID',   p.customer_id],
          ['Model ID',      p.model_id],
          ['Requested at',  p.requested_at],
          ['Churn prob.',   p.churn_probability.toFixed(6)],
          ['Threshold',     p.threshold_used.toFixed(4)],
        ]}/>
        <hr className="hr"/>
        <div>
          <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Payload (preview)</div>
          <CodeBlock lang="json" height={120}>{JSON.stringify({
            prediction_id:    p.id,
            customer_id:      p.customer_id,
            churn_probability: p.churn_probability,
            churn_pred:       p.churn_pred,
            threshold_used:   p.threshold_used,
            requested_at:     p.requested_at,
          }, null, 2)}</CodeBlock>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn btn-sm" style={{ flex: 1 }}
            onClick={() => navigator.clipboard.writeText(p.id)}>
            <Icon name="copy" size={11}/> Copy ID
          </button>
          <button className="btn btn-sm" style={{ flex: 1 }}>
            <Icon name="external" size={11}/> Trace
          </button>
        </div>
      </div>
    </SectionCard>
  )
}
