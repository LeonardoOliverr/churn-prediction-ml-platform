import { useState } from 'react'
import {
  Icon, StatusBadge, SectionCard, KV, CodeBlock, Pill,
  Table, Th, Td, Tr,
} from '@/components/primitives'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from '@/hooks/useApiKeys'
import { useAuthStore } from '@/store/authStore'
import type { ApiKeyRecord, ApiKeyResponse, ApiScope } from '@/types/api'

const ALL_SCOPES: ApiScope[] = ['predict', 'predictions:read']

const AUDIT_LOG = [
  { t: '2026-05-14 09:11', ev: 'key.use',    actor: 'system',    ip: '10.4.118.22',  ua: 'go-grpc/1.62'    },
  { t: '2026-05-14 07:12', ev: 'key.create', actor: 'm.tanaka',  ip: '203.0.113.7',  ua: 'control-plane'   },
  { t: '2026-05-13 22:48', ev: 'key.use',    actor: 'ci-runner', ip: '10.7.0.4',     ua: 'okhttp/4.12'     },
  { t: '2026-05-13 18:01', ev: 'key.revoke', actor: 'r.almeida', ip: '10.7.0.18',    ua: 'control-plane'   },
]

function evTone(ev: string) {
  if (ev === 'key.revoke') return 'crit'
  if (ev === 'key.create') return 'accent'
  return 'neutral'
}

export function ApiKeysPage() {
  const { selectedTenantId } = useAuthStore()
  const { data: keys = [], isLoading } = useApiKeys()
  const createKey = useCreateApiKey()
  const revokeKey = useRevokeApiKey()

  const [newOpen,    setNewOpen]    = useState(false)
  const [revokeItem, setRevokeItem] = useState<ApiKeyRecord | null>(null)
  const [revealed,   setRevealed]   = useState<ApiKeyResponse | null>(null)

  const active  = keys.filter(k => k.is_active)
  const revoked = keys.filter(k => !k.is_active)

  async function handleCreate(payload: { scopes: ApiScope[]; description: string; expires_at: string | null }) {
    if (!selectedTenantId) return
    const res = await createKey.mutateAsync({ tenant_id: selectedTenantId, ...payload })
    setNewOpen(false)
    setRevealed(res)
  }

  async function handleRevoke() {
    if (!revokeItem) return
    await revokeKey.mutateAsync(revokeItem.id)
    setRevokeItem(null)
  }

  const stale = active.filter(k => {
    if (!k.last_used_at) return true
    return (Date.now() - new Date(k.last_used_at).getTime()) > 30 * 24 * 60 * 60 * 1000
  })

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>
      {/* Security posture strip */}
      <div className="card" style={{
        padding: '14px 18px', display: 'grid',
        gridTemplateColumns: 'auto 1fr auto auto auto auto',
        gap: 20, alignItems: 'center',
      }}>
        <Icon name="shield" size={20} style={{ color: 'var(--accent-fg)' }}/>
        <div>
          <div style={{ fontSize: 13, color: 'var(--fg-1)', fontWeight: 500 }}>Key security posture</div>
          <div style={{ fontSize: 11, color: 'var(--fg-3)', marginTop: 2 }}>
            {stale.length > 0
              ? `${stale.length} key${stale.length > 1 ? 's' : ''} are stale (>30d unused). Consider rotating.`
              : 'No stale or unrotated keys detected.'}
          </div>
        </div>
        <SecurityStat label="Active"  value={active.length}  tone="ok"/>
        <SecurityStat label="Stale"   value={stale.length}   tone="amber"/>
        <SecurityStat label="Revoked" value={revoked.length} tone="crit"/>
        <button className="btn btn-primary" onClick={() => setNewOpen(true)}>
          <Icon name="plus" size={12}/> Create key
        </button>
      </div>

      {/* Keys table */}
      <SectionCard title="API Keys" pad={false}
        action={<span style={{ fontSize: 10, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)' }}>{keys.length} keys</span>}
      >
        {isLoading && (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>Loading…</div>
        )}
        <Table>
          <thead>
            <tr>
              <Th>Prefix</Th>
              <Th>Scopes</Th>
              <Th>Project</Th>
              <Th align="right">Created</Th>
              <Th align="right">Last used</Th>
              <Th align="right">Expires</Th>
              <Th align="right">Status</Th>
              <Th w={28}></Th>
            </tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <Tr key={k.id}>
                <Td mono style={{ color: 'var(--fg-2)', fontSize: 11 }}>
                  {k.key_prefix}••••••••
                </Td>
                <Td>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {k.scopes.map(s => <span key={s} className="tag mono">{s}</span>)}
                  </div>
                </Td>
                <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{k.project_id?.slice(0, 8) ?? '—'}</Td>
                <Td mono align="right" style={{ color: 'var(--fg-3)', fontSize: 11 }}>{k.created_at.slice(0, 10)}</Td>
                <Td mono align="right" style={{ color: 'var(--fg-3)', fontSize: 11 }}>{k.last_used_at?.slice(0, 10) ?? '—'}</Td>
                <Td mono align="right" style={{ color: 'var(--fg-3)', fontSize: 11 }}>{k.expires_at?.slice(0, 10) ?? 'never'}</Td>
                <Td align="right"><StatusBadge status={k.is_active ? 'active' : 'retired'} size="xs"/></Td>
                <Td>
                  {k.is_active && (
                    <button className="btn btn-ghost btn-sm" onClick={() => setRevokeItem(k)} style={{ padding: 3 }} title="Revoke">
                      <Icon name="trash" size={11}/>
                    </button>
                  )}
                </Td>
              </Tr>
            ))}
            {!isLoading && keys.length === 0 && (
              <tr>
                <td colSpan={8} style={{ padding: 32, textAlign: 'center', color: 'var(--fg-4)', fontSize: 12 }}>
                  No API keys. Create one to start making predictions.
                </td>
              </tr>
            )}
          </tbody>
        </Table>
      </SectionCard>

      {/* Audit log */}
      <SectionCard title="Recent key events" pad={false}>
        <Table>
          <thead>
            <tr>
              <Th>Time UTC</Th>
              <Th>Event</Th>
              <Th>Actor</Th>
              <Th>IP</Th>
              <Th>User-agent</Th>
            </tr>
          </thead>
          <tbody>
            {AUDIT_LOG.map((r, i) => (
              <Tr key={i}>
                <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{r.t}</Td>
                <Td><Pill tone={evTone(r.ev) as any}>{r.ev}</Pill></Td>
                <Td mono style={{ color: 'var(--fg-2)' }}>{r.actor}</Td>
                <Td mono style={{ color: 'var(--fg-3)' }}>{r.ip}</Td>
                <Td mono style={{ color: 'var(--fg-4)', fontSize: 11 }}>{r.ua}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      </SectionCard>

      {/* Create dialog */}
      <CreateKeyDialog open={newOpen} onClose={() => setNewOpen(false)} onCreate={handleCreate} isPending={createKey.isPending}/>

      {/* Revoke dialog */}
      <Dialog open={!!revokeItem} onOpenChange={() => setRevokeItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API key</DialogTitle>
            <DialogDescription>
              This will immediately reject all requests using <span className="mono">{revokeItem?.key_prefix}••••••••</span>. Not reversible.
            </DialogDescription>
          </DialogHeader>
          <div style={{ display: 'flex', gap: 8, background: 'var(--crit-soft)', border: '1px solid var(--crit-line)', borderRadius: 4, padding: '10px 12px', fontSize: 12, color: 'var(--crit-fg)' }}>
            <Icon name="alert" size={13}/>
            <span>Revocation is auditable and irreversible.</span>
          </div>
          {revokeItem && (
            <KV mono items={[
              ['Key prefix', `${revokeItem.key_prefix}••••`],
              ['Created',    revokeItem.created_at.slice(0, 10)],
              ['Scopes',     revokeItem.scopes.join(', ')],
            ]}/>
          )}
          <DialogFooter>
            <button className="btn" onClick={() => setRevokeItem(null)}>Cancel</button>
            <button className="btn btn-danger" onClick={handleRevoke} disabled={revokeKey.isPending}>
              <Icon name="trash" size={12}/> {revokeKey.isPending ? 'Revoking…' : 'Revoke immediately'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reveal dialog */}
      <Dialog open={!!revealed} onOpenChange={() => setRevealed(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>API key created — copy now</DialogTitle>
            <DialogDescription>The full secret is shown once. We do not store it.</DialogDescription>
          </DialogHeader>
          <div style={{ padding: '10px 12px', background: 'var(--warn-soft)', border: '1px solid var(--warn-line)', borderRadius: 4, fontSize: 12, color: 'var(--warn-fg)', display: 'flex', gap: 8 }}>
            <Icon name="alert" size={13}/>
            <span>Store in your secrets manager — it cannot be recovered after closing.</span>
          </div>
          {revealed && (
            <CodeBlock lang="bash">{`export API_KEY="${revealed.secret}"\n\ncurl -X POST /api/predict \\\n  -H "x-api-key: $API_KEY" \\\n  -H "Content-Type: application/json"`}</CodeBlock>
          )}
          <DialogFooter>
            <button className="btn" onClick={() => revealed && navigator.clipboard.writeText(revealed.secret)}>
              <Icon name="copy" size={12}/> Copy secret
            </button>
            <button className="btn btn-primary" onClick={() => setRevealed(null)}>Done</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function SecurityStat({ label, value, tone }: { label: string; value: number; tone: 'ok' | 'amber' | 'crit' }) {
  const c = tone === 'ok' ? 'var(--ok-fg)' : tone === 'amber' ? 'var(--warn-fg)' : 'var(--crit-fg)'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
      <span className="num" style={{ fontSize: 18, color: c }}>{value}</span>
      <span style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
    </div>
  )
}

function CreateKeyDialog({ open, onClose, onCreate, isPending }: {
  open: boolean; onClose: () => void
  onCreate: (p: { scopes: ApiScope[]; description: string; expires_at: string | null }) => void
  isPending: boolean
}) {
  const [description, setDescription] = useState('')
  const [scopes, setScopes] = useState<ApiScope[]>(['predict'])
  const [expiry, setExpiry] = useState('90d')

  function toggleScope(s: ApiScope) {
    setScopes(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  }

  function expiryDate() {
    if (expiry === 'never') return null
    const days = expiry === '30d' ? 30 : expiry === '90d' ? 90 : 180
    const d = new Date()
    d.setDate(d.getDate() + days)
    return d.toISOString()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create API key</DialogTitle>
          <DialogDescription>The secret will be shown once on creation.</DialogDescription>
        </DialogHeader>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <FormField label="Description">
            <input className="input mono" placeholder="e.g. fraud-prod / gateway"
              value={description} onChange={e => setDescription(e.target.value)}/>
          </FormField>
          <FormField label="Scopes">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {ALL_SCOPES.map(s => {
                const active = scopes.includes(s)
                return (
                  <button key={s} onClick={() => toggleScope(s)} style={{
                    padding: '4px 8px', fontSize: 11, fontFamily: 'var(--font-mono)',
                    background: active ? 'var(--accent-soft)' : 'var(--bg-inset)',
                    border: '1px solid', borderColor: active ? 'var(--accent-line)' : 'var(--border-1)',
                    borderRadius: 3, color: active ? 'var(--accent-fg)' : 'var(--fg-3)', cursor: 'pointer',
                  }}>{active ? '✓ ' : ''}{s}</button>
                )
              })}
            </div>
          </FormField>
          <FormField label="Expiration">
            <div style={{ display: 'flex', gap: 6 }}>
              {[['30d','30 days'], ['90d','90 days (rec.)'], ['180d','180 days'], ['never','Never']].map(([v, label]) => (
                <button key={v} onClick={() => setExpiry(v)} className="btn btn-sm" style={{
                  background: expiry === v ? 'var(--bg-3)' : 'var(--bg-inset)',
                  borderColor: expiry === v ? 'var(--accent-line)' : 'var(--border-1)',
                  color: expiry === v ? 'var(--fg-1)' : 'var(--fg-3)',
                  flex: 1, justifyContent: 'center',
                }}>{label}</button>
              ))}
            </div>
          </FormField>
          <div style={{ padding: '10px 12px', background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', borderRadius: 4, fontSize: 12, color: 'var(--fg-2)', display: 'flex', gap: 8 }}>
            <Icon name="info" size={13} style={{ color: 'var(--accent-fg)' }}/>
            <span>Secret shown once on creation. Store in your secrets manager — it cannot be recovered.</span>
          </div>
        </div>
        <DialogFooter>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => onCreate({ scopes, description, expires_at: expiryDate() })}
            disabled={isPending || scopes.length === 0}>
            <Icon name="key" size={12}/> {isPending ? 'Generating…' : 'Generate key'}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 10, color: 'var(--fg-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      {children}
    </div>
  )
}
