import { useState } from 'react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import {
  Icon, StatusBadge, SectionCard, TenantAvatar, Sparkline,
  Table, Th, Td, Tr, fmt, sparkline,
} from '@/components/primitives'
import { useAuthStore } from '@/store/authStore'
import { useCreateTenant, useCreateProject } from '@/hooks/useTenants'

const GOVERNANCE_ROWS = [
  { k: 'Encryption',       v: 'KMS · per-tenant CMK'          },
  { k: 'Audit retention',  v: '7y · WORM'                     },
  { k: 'PII handling',     v: 'tokenized in transit + at rest' },
  { k: 'Data residency',   v: 'configurable per project'       },
]

export function TenantsPage() {
  const { knownTenants, knownProjects, selectedTenantId, selectTenant, selectProject } = useAuthStore()
  const createTenant  = useCreateTenant()
  const createProject = useCreateProject()

  const [tenantOpen,  setTenantOpen]  = useState(false)
  const [projectOpen, setProjectOpen] = useState(false)
  const [tName, setTName]             = useState('')
  const [tSlug, setTSlug]             = useState('')
  const [pName, setPName]             = useState('')
  const [pSlug, setPSlug]             = useState('')

  const activeTenant   = knownTenants.find(t => t.id === selectedTenantId) ?? knownTenants[0]
  const tenantProjects = knownProjects.filter(p => p.tenant_id === activeTenant?.id)

  async function handleCreateTenant() {
    if (!tName.trim() || !tSlug.trim()) return
    await createTenant.mutateAsync({ name: tName.trim(), slug: tSlug.trim() })
    setTName(''); setTSlug(''); setTenantOpen(false)
  }

  async function handleCreateProject() {
    if (!activeTenant || !pName.trim() || !pSlug.trim()) return
    await createProject.mutateAsync({ tenant_id: activeTenant.id, name: pName.trim(), slug: pSlug.trim() })
    setPName(''); setPSlug(''); setProjectOpen(false)
  }

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 14, color: 'var(--fg-1)', fontWeight: 500 }}>Tenants &amp; isolation</div>
          <div style={{ fontSize: 12, color: 'var(--fg-3)', marginTop: 2 }}>
            {knownTenants.length} tenant{knownTenants.length !== 1 ? 's' : ''} · {knownProjects.length} project{knownProjects.length !== 1 ? 's' : ''}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={() => setTenantOpen(true)}>
            <Icon name="plus" size={12}/> Onboard tenant
          </button>
        </div>
      </div>

      {/* Tenant list */}
      <SectionCard pad={false}>
        {knownTenants.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>
            No tenants loaded. Log in with a JWT to load tenant data.
          </div>
        )}
        {knownTenants.map((t, i) => {
          const projects = knownProjects.filter(p => p.tenant_id === t.id)
          const traffic  = sparkline(t.id.charCodeAt(0) + i * 7, 32, 40, 18)
          const isSel    = selectedTenantId === t.id
          const initials = t.name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
          return (
            <div key={t.id}
              onClick={() => { selectTenant(t.id); if (projects[0]) selectProject(projects[0].id) }}
              style={{
                padding: '16px 20px',
                borderBottom: i < knownTenants.length - 1 ? '1px solid var(--divider)' : 'none',
                background:   isSel ? 'var(--bg-3)' : 'transparent',
                borderLeft:   '2px solid', borderLeftColor: isSel ? 'var(--accent-fg)' : 'transparent',
                cursor: 'pointer',
                display: 'grid',
                gridTemplateColumns: 'auto minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr) auto',
                gap: 24, alignItems: 'center',
              }}>
              <TenantAvatar initials={initials} size={36}/>
              <div>
                <div style={{ fontSize: 14, color: 'var(--fg-1)', fontWeight: 500 }}>{t.name}</div>
                <div style={{ fontSize: 11, color: 'var(--fg-4)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                  {t.id} · {t.slug}
                </div>
              </div>
              <TenantCell label="Projects">{projects.length} project{projects.length !== 1 ? 's' : ''}</TenantCell>
              <TenantCell label="Predictions 24h">
                <span className="num">{fmt.compact(Math.floor(Math.random() * 50000 + 5000))}</span>
                <Sparkline data={traffic} width={80} height={18} strokeWidth={1} color="var(--accent-fg)" fill={false}/>
              </TenantCell>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <StatusBadge status="healthy" size="xs"/>
                <Icon name="chev-right" size={14} style={{ color: 'var(--fg-4)' }}/>
              </div>
            </div>
          )
        })}
      </SectionCard>

      {/* Detail panel */}
      {activeTenant && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>
          <SectionCard title={`Projects · ${activeTenant.name}`} pad={false}
            action={<button className="btn btn-sm" onClick={() => setProjectOpen(true)}><Icon name="plus" size={11}/> Project</button>}
          >
            <Table>
              <thead>
                <tr>
                  <Th>Project</Th>
                  <Th>Slug</Th>
                  <Th align="right">ID</Th>
                  <Th w={28}></Th>
                </tr>
              </thead>
              <tbody>
                {tenantProjects.map(p => (
                  <Tr key={p.id}>
                    <Td mono>
                      <span style={{ color: 'var(--fg-1)' }}>{p.name}</span>
                    </Td>
                    <Td mono style={{ color: 'var(--fg-2)', fontSize: 11 }}>{p.slug}</Td>
                    <Td mono align="right" style={{ color: 'var(--fg-4)', fontSize: 11 }}>{p.id.slice(0, 12)}…</Td>
                    <Td>
                      <button className="btn btn-ghost btn-sm" onClick={() => selectProject(p.id)} style={{ padding: 3 }} title="Switch to project">
                        <Icon name="chev-right" size={11}/>
                      </button>
                    </Td>
                  </Tr>
                ))}
                {tenantProjects.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ padding: 24, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>
                      No projects. Click "+ Project" to create one.
                    </td>
                  </tr>
                )}
              </tbody>
            </Table>
          </SectionCard>

          <SectionCard title="Governance" pad={false}>
            <div>
              {[
                { k: 'Tenant ID',   v: activeTenant.id },
                { k: 'Slug',        v: activeTenant.slug },
                { k: 'Projects',    v: `${tenantProjects.length}` },
                ...GOVERNANCE_ROWS,
              ].map((r, i, arr) => (
                <div key={r.k} style={{
                  padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  borderBottom: i < arr.length - 1 ? '1px solid var(--divider)' : 'none', fontSize: 12,
                }}>
                  <span style={{ color: 'var(--fg-3)' }}>{r.k}</span>
                  <span className="mono" style={{ color: 'var(--fg-1)' }}>{r.v}</span>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      )}

      {/* Create tenant dialog */}
      <Dialog open={tenantOpen} onOpenChange={setTenantOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Onboard tenant</DialogTitle>
            <DialogDescription>Create a new isolated tenant namespace.</DialogDescription>
          </DialogHeader>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <DlgField label="Name">
              <input className="input" placeholder="e.g. IBM Telco" value={tName} onChange={e => { setTName(e.target.value); if (!tSlug) setTSlug(e.target.value.toLowerCase().replace(/\s+/g, '-')) }}/>
            </DlgField>
            <DlgField label="Slug">
              <input className="input mono" placeholder="e.g. ibm-telco" value={tSlug} onChange={e => setTSlug(e.target.value)}/>
            </DlgField>
          </div>
          <DialogFooter>
            <button className="btn" onClick={() => setTenantOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCreateTenant}
              disabled={createTenant.isPending || !tName.trim() || !tSlug.trim()}>
              <Icon name="plus" size={12}/> {createTenant.isPending ? 'Creating…' : 'Create tenant'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create project dialog */}
      <Dialog open={projectOpen} onOpenChange={setProjectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create project</DialogTitle>
            <DialogDescription>Projects live inside a tenant and scope model configs and API keys.</DialogDescription>
          </DialogHeader>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <DlgField label={`Tenant · ${activeTenant?.name ?? ''}`}>
              <div className="input mono" style={{ color: 'var(--fg-3)', cursor: 'default' }}>{activeTenant?.id}</div>
            </DlgField>
            <DlgField label="Name">
              <input className="input" placeholder="e.g. telco-churn-2024" value={pName} onChange={e => { setPName(e.target.value); if (!pSlug) setPSlug(e.target.value.toLowerCase().replace(/\s+/g, '-')) }}/>
            </DlgField>
            <DlgField label="Slug">
              <input className="input mono" placeholder="e.g. telco-churn-2024" value={pSlug} onChange={e => setPSlug(e.target.value)}/>
            </DlgField>
          </div>
          <DialogFooter>
            <button className="btn" onClick={() => setProjectOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCreateProject}
              disabled={createProject.isPending || !pName.trim() || !pSlug.trim() || !activeTenant}>
              <Icon name="plus" size={12}/> {createProject.isPending ? 'Creating…' : 'Create project'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function TenantCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 12, color: 'var(--fg-1)', marginTop: 2, display: 'flex', gap: 10, alignItems: 'center' }}>{children}</div>
    </div>
  )
}

function DlgField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 10, color: 'var(--fg-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      {children}
    </div>
  )
}
