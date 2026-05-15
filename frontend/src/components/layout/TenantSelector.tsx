import { useState, useRef, useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'
import { Icon, TenantAvatar } from '@/components/primitives'

export function TenantSelector() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { knownTenants, knownProjects, selectedTenantId, selectedProjectId, selectTenant, selectProject } = useAuthStore()

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const activeTenant = knownTenants.find(t => t.id === selectedTenantId)
  const tenantProjects = knownProjects.filter(p => p.tenant_id === selectedTenantId)
  const activeProject = tenantProjects.find(p => p.id === selectedProjectId)

  const initials = activeTenant
    ? activeTenant.name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : 'ML'

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 10px', background: 'var(--bg-2)',
        border: '1px solid var(--border-2)', borderRadius: 5,
        cursor: 'pointer', color: 'var(--fg-1)', fontFamily: 'inherit', textAlign: 'left',
      }}>
        <TenantAvatar initials={initials} size={22}/>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {activeTenant?.name || 'Select tenant'}
          </div>
          <div style={{ fontSize: 10, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)', display: 'flex', gap: 5, alignItems: 'center' }}>
            <span>{activeProject?.name || 'no project'}</span>
          </div>
        </div>
        <Icon name="chev-down" size={12} style={{ color: 'var(--fg-3)' }}/>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
          background: 'var(--bg-2)', border: '1px solid var(--border-2)',
          borderRadius: 6, boxShadow: 'var(--shadow-pop)', zIndex: 50,
          maxHeight: 360, overflow: 'auto', animation: 'fade-in 120ms ease-out',
        }}>
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--divider)', fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Tenants
          </div>
          {knownTenants.length === 0 && (
            <div style={{ padding: '12px 10px', fontSize: 12, color: 'var(--fg-4)', textAlign: 'center' }}>No tenants loaded</div>
          )}
          {knownTenants.map(t => {
            const isCurrent = t.id === selectedTenantId
            const ti = t.name.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
            return (
              <button key={t.id} onClick={() => { selectTenant(t.id); setOpen(false) }} style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 10px', background: isCurrent ? 'var(--bg-3)' : 'transparent',
                border: 'none', color: 'var(--fg-1)', cursor: 'pointer', textAlign: 'left',
              }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-3)'}
                onMouseLeave={e => { if (!isCurrent) (e.currentTarget as HTMLElement).style.background = 'transparent' }}>
                <TenantAvatar initials={ti} size={22}/>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: 'var(--fg-1)' }}>{t.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)' }}>{t.slug}</div>
                </div>
                {isCurrent && <Icon name="check" size={12} style={{ color: 'var(--accent-fg)' }}/>}
              </button>
            )
          })}

          {tenantProjects.length > 0 && (
            <>
              <div style={{ padding: '6px 10px', borderTop: '1px solid var(--divider)', fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Projects · {activeTenant?.name}
              </div>
              {tenantProjects.map(p => (
                <button key={p.id} onClick={() => { selectProject(p.id); setOpen(false) }} style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                  padding: '6px 10px', background: 'transparent',
                  border: 'none', color: 'var(--fg-2)', cursor: 'pointer', textAlign: 'left',
                  fontFamily: 'var(--font-mono)', fontSize: 11,
                }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-3)'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}>
                  <span style={{ width: 4, height: 4, borderRadius: 999, background: p.id === selectedProjectId ? 'var(--accent-fg)' : 'var(--fg-5)', flexShrink: 0 }}/>
                  <span style={{ flex: 1 }}>{p.name}</span>
                  {p.id === selectedProjectId && <span style={{ fontSize: 9, color: 'var(--accent-fg)' }}>ACTIVE</span>}
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
