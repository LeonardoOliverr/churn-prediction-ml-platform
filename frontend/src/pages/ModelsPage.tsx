import { useState, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Icon, StatusBadge, SectionCard, Sparkline,
  Table, Th, Td, Tr, sparkline,
} from '@/components/primitives'
import { useAuthStore } from '@/store/authStore'
import { listModelConfig } from '@/services/admin'
import type { ProjectModelConfigRecord } from '@/types/api'
import { PromoteDialog } from '@/components/models/PromoteDialog'
import { ConfigureModelDialog } from '@/components/models/ConfigureModelDialog'
import { DeactivateDialog } from '@/components/models/DeactivateDialog'

export function ModelsPage() {
  const { selectedTenantId, selectedProjectId } = useAuthStore()
  const queryClient = useQueryClient()

  const [view, setView] = useState<'compare' | 'lifecycle'>('compare')
  const [promoteOpen, setPromoteOpen] = useState(false)
  const [configureOpen, setConfigureOpen] = useState(false)
  const [configureRole, setConfigureRole] = useState<'champion' | 'challenger'>('champion')
  const [deactivateOpen, setDeactivateOpen] = useState(false)
  const [deactivateModel_, setDeactivateModel] = useState<ProjectModelConfigRecord | null>(null)

  const { data: config, isLoading } = useQuery({
    queryKey: ['model-config', selectedTenantId, selectedProjectId],
    queryFn: () => listModelConfig(selectedTenantId!, selectedProjectId),
    enabled: !!selectedTenantId,
  })

  const champion   = config?.champion
  const challenger = config?.challenger
  const history    = config?.history ?? []
  const allModels  = [champion, challenger, ...history.filter(h => h.id !== champion?.id && h.id !== challenger?.id)].filter(Boolean) as ProjectModelConfigRecord[]

  function handleDeactivate(m: ProjectModelConfigRecord) {
    setDeactivateModel(m)
    setDeactivateOpen(true)
  }

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div style={{ fontSize: 14, color: 'var(--fg-1)', fontWeight: 500 }}>
            Model registry · <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg-3)' }}>{selectedProjectId || 'all projects'}</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--fg-3)', marginTop: 2 }}>
            {allModels.length} models · {champion ? 1 : 0} champion · {challenger ? 1 : 0} challenger
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={() => { setConfigureRole('champion'); setConfigureOpen(true) }}>
            <Icon name="code" size={12}/> Configure champion
          </button>
          <button className="btn" onClick={() => { setConfigureRole('challenger'); setConfigureOpen(true) }}>
            <Icon name="code" size={12}/> Configure challenger
          </button>
          <button className="btn btn-primary" onClick={() => setPromoteOpen(true)} disabled={!challenger}>
            <Icon name="promote" size={12}/> Promote challenger
          </button>
        </div>
      </div>

      {/* View switcher */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: 3, background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 6, width: 'fit-content' }}>
        {[{ id: 'compare', label: 'Side-by-side', icon: 'swap' }, { id: 'lifecycle', label: 'Lifecycle', icon: 'promote' }].map(v => (
          <button key={v.id} onClick={() => setView(v.id as any)} className="btn btn-sm" style={{
            background: view === v.id ? 'var(--bg-3)' : 'transparent',
            borderColor: view === v.id ? 'var(--border-2)' : 'transparent',
            color: view === v.id ? 'var(--fg-1)' : 'var(--fg-3)',
          }}>
            <Icon name={v.icon} size={11}/> {v.label}
          </button>
        ))}
      </div>

      {/* Compare view */}
      {view === 'compare' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>
          <ModelRoleCard model={champion} role="champion" actions={
            <button className="btn btn-sm" onClick={() => { setConfigureRole('champion'); setConfigureOpen(true) }}>
              <Icon name="code" size={11}/> Configure
            </button>
          }/>
          <ModelRoleCard model={challenger} role="challenger" compareTo={champion ?? undefined} actions={
            <>
              {challenger && <button className="btn btn-sm" onClick={() => handleDeactivate(challenger)}><Icon name="x" size={11}/> Deactivate</button>}
              <button className="btn btn-primary btn-sm" onClick={() => setPromoteOpen(true)} disabled={!challenger}>
                <Icon name="promote" size={11}/> Promote
              </button>
            </>
          }/>
        </div>
      )}

      {/* Lifecycle view */}
      {view === 'lifecycle' && (
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, position: 'relative' }}>
            <div style={{ position: 'absolute', top: 17, left: '16.6%', right: '16.6%', height: 1, background: 'var(--border-2)', zIndex: 0 }}/>
            {[
              { id: 'challenger', label: 'Challenger', desc: 'Shadow traffic', model: challenger },
              { id: 'champion',   label: 'Champion',   desc: 'Production',     model: champion },
              { id: 'retired',    label: 'Retired',    desc: 'Archived',       model: history.find(h => !h.is_active) ?? null },
            ].map((s, i) => (
              <div key={s.id} style={{ display: 'flex', flexDirection: 'column', gap: 14, position: 'relative', zIndex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{
                    width: 34, height: 34, borderRadius: 999,
                    background: s.id === 'champion' ? 'var(--accent-soft)' : s.id === 'challenger' ? 'var(--warn-soft)' : 'var(--bg-2)',
                    border: '1px solid', borderColor: s.id === 'champion' ? 'var(--accent-line)' : s.id === 'challenger' ? 'var(--warn-line)' : 'var(--border-2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: s.id === 'champion' ? 'var(--accent-fg)' : s.id === 'challenger' ? 'var(--warn-fg)' : 'var(--fg-2)',
                  }}>
                    <span className="num" style={{ fontSize: 11, fontWeight: 600 }}>0{i + 1}</span>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--fg-1)', fontWeight: 500 }}>{s.label}</div>
                    <div style={{ fontSize: 10, color: 'var(--fg-4)' }}>{s.desc}</div>
                  </div>
                </div>
                {s.model ? (
                  <div style={{ padding: '8px 10px', background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 4 }}>
                    <div className="mono" style={{ fontSize: 11, color: 'var(--fg-1)' }}>{s.model.model_name}@{s.model.model_version}</div>
                    <div style={{ fontSize: 10, color: 'var(--fg-4)', marginTop: 2 }}>{s.model.configured_at?.slice(0, 10)} · {s.model.configured_by}</div>
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: 'var(--fg-5)', padding: '8px 10px', background: 'var(--bg-inset)', border: '1px dashed var(--border-1)', borderRadius: 4, textAlign: 'center' }}>—</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All models table */}
      <SectionCard title="All models" pad={false}>
        <Table>
          <thead>
            <tr>
              <Th>Model</Th>
              <Th>Role</Th>
              <Th align="right">Version</Th>
              <Th align="right">Threshold</Th>
              <Th align="right">Traffic</Th>
              <Th>Environment</Th>
              <Th>Configured</Th>
              <Th>By</Th>
              <Th w={32}></Th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={9} style={{ padding: 24, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>Loading…</td></tr>
            )}
            {allModels.map(m => (
              <Tr key={m.id}>
                <Td mono><span style={{ color: 'var(--fg-1)' }}>{m.model_name}</span></Td>
                <Td><StatusBadge status={m.role} size="xs"/></Td>
                <Td mono align="right" style={{ color: 'var(--fg-2)' }}>{m.model_version}</Td>
                <Td mono align="right">{m.threshold.toFixed(2)}</Td>
                <Td mono align="right" style={{ color: 'var(--fg-3)' }}>{(m.traffic_split * 100).toFixed(0)}%</Td>
                <Td style={{ color: 'var(--fg-3)', fontSize: 12 }}>{m.environment}</Td>
                <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{m.configured_at?.slice(0, 10)}</Td>
                <Td style={{ color: 'var(--fg-3)', fontSize: 11 }}>{m.configured_by}</Td>
                <Td>
                  {m.is_active && (
                    <button className="btn btn-ghost btn-sm" onClick={() => handleDeactivate(m)} style={{ padding: 3 }}>
                      <Icon name="x" size={11}/>
                    </button>
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      </SectionCard>

      {/* Dialogs */}
      <PromoteDialog
        open={promoteOpen}
        onClose={() => { setPromoteOpen(false); queryClient.invalidateQueries({ queryKey: ['model-config'] }) }}
        modelId={challenger?.id ?? ''}
        modelName={challenger?.model_name ?? ''}
      />
      <ConfigureModelDialog
        open={configureOpen}
        onClose={() => { setConfigureOpen(false); queryClient.invalidateQueries({ queryKey: ['model-config'] }) }}
        role={configureRole}
      />
      <DeactivateDialog
        open={deactivateOpen}
        onClose={() => { setDeactivateOpen(false); queryClient.invalidateQueries({ queryKey: ['model-config'] }) }}
        modelId={deactivateModel_?.id ?? ''}
        modelName={deactivateModel_?.model_name ?? ''}
        role={deactivateModel_?.role ?? 'champion'}
      />
    </div>
  )
}

/* ── ModelRoleCard ── */
function ModelRoleCard({ model, role, compareTo, actions }: {
  model: ProjectModelConfigRecord | null | undefined
  role: 'champion' | 'challenger'
  compareTo?: ProjectModelConfigRecord
  actions: React.ReactNode
}) {
  const traffic = useMemo(() => sparkline(role === 'champion' ? 17 : 43, 36, 50, 18), [role])

  if (!model) {
    return (
      <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--fg-4)' }}>
        <Icon name="git-branch" size={16}/>
        <div style={{ fontSize: 12 }}>No {role} configured</div>
      </div>
    )
  }

  const headerBg = role === 'champion'
    ? 'linear-gradient(180deg, color-mix(in oklab, var(--accent-soft) 30%, transparent), transparent)'
    : 'linear-gradient(180deg, color-mix(in oklab, var(--warn-soft) 30%, transparent), transparent)'

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--divider)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, background: headerBg }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <StatusBadge status={role}/>
          <div>
            <div className="mono" style={{ fontSize: 13, color: 'var(--fg-1)', fontWeight: 500 }}>
              {model.model_name}<span style={{ color: 'var(--fg-4)' }}>@</span>{model.model_version}
            </div>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
              {model.id.slice(0, 12)} · {model.environment}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>{actions}</div>
      </div>

      {/* Metric grid (threshold + traffic) */}
      <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
        <ModelMetric label="Threshold" value={model.threshold.toFixed(2)}
          delta={compareTo ? +(model.threshold - compareTo.threshold).toFixed(3) : null}
          better={compareTo ? model.threshold < compareTo.threshold : null}/>
        <ModelMetric label="Traffic split" value={`${(model.traffic_split * 100).toFixed(0)}%`}/>
      </div>

      {/* Traffic sparkline */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--divider)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Traffic · simulated</span>
          <span className="num" style={{ fontSize: 11, color: 'var(--fg-2)' }}>{(model.traffic_split * 100).toFixed(0)}%</span>
        </div>
        <Sparkline data={traffic} width={420} height={36} color={role === 'champion' ? 'var(--accent-fg)' : 'var(--warn-fg)'}/>
      </div>

      {/* Threshold bar */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--divider)' }}>
        <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Decision threshold</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 4, background: 'var(--bg-3)', borderRadius: 999, position: 'relative' }}>
            <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${model.threshold * 100}%`, background: 'var(--accent-fg)', borderRadius: 999 }}/>
            <div style={{ position: 'absolute', left: `${model.threshold * 100}%`, top: -3, width: 2, height: 10, background: 'var(--fg-1)' }}/>
          </div>
          <span className="num" style={{ fontSize: 12, color: 'var(--fg-1)' }}>{model.threshold.toFixed(2)}</span>
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '10px 16px', borderTop: '1px solid var(--divider)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: 'var(--fg-3)' }}>
        <span style={{ fontFamily: 'var(--font-mono)' }}>configured {model.configured_at?.slice(0, 10)} · {model.configured_by}</span>
        <StatusBadge status={model.is_active ? 'active' : 'retired'} size="xs"/>
      </div>
    </div>
  )
}

function ModelMetric({ label, value, delta, better }: { label: string; value: string; delta?: number | null; better?: boolean | null }) {
  const positive = delta != null && delta > 0
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 500 }}>{label}</div>
      <div className="num" style={{ fontSize: 18, color: 'var(--fg-1)', marginTop: 2, fontWeight: 500 }}>{value}</div>
      {delta != null && (
        <div className="num" style={{ fontSize: 10, marginTop: 2, color: better ? 'var(--ok-fg)' : better === false ? 'var(--crit-fg)' : 'var(--fg-4)' }}>
          {positive ? '+' : ''}{delta}
        </div>
      )}
    </div>
  )
}
