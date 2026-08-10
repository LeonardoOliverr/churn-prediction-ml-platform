import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Icon, Pill } from '@/components/primitives'
import { useAuthStore } from '@/store/authStore'

const TITLES: Record<string, [string, string]> = {
  '/dashboard':  ['Overview',    'Operational cockpit'],
  '/models':     ['Models',      'Champion / challenger lifecycle'],
  '/predict':    ['Predict',     'Endpoint simulation'],
  '/predictions':['Predictions', 'Audit & traceability'],
  '/health':     ['Health',      'Endpoint & infrastructure'],
  '/api-keys':   ['API Keys',    'Credentials & scopes'],
  '/tenants':    ['Tenants',     'Multi-tenant administration'],
}

export function Topbar() {
  const location = useLocation()
  const [title, sub] = TITLES[location.pathname] || ['', '']
  const [now, setNow] = useState(new Date())
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const utc = now.toISOString().replace('T', ' ').slice(0, 19) + ' UTC'

  return (
    <header style={{
      height: 'var(--topbar-h)', minHeight: 'var(--topbar-h)',
      background: 'var(--bg-1)', borderBottom: '1px solid var(--border-1)',
      padding: '0 18px', display: 'flex', alignItems: 'center', gap: 16,
    }}>
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flexShrink: 1, overflow: 'hidden' }}>
        <span style={{ fontSize: 11, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
          {selectedTenantId || 'ibm-telco'}
        </span>
        <Icon name="chev-right" size={10} style={{ color: 'var(--fg-5)' }}/>
        <span style={{ fontSize: 11, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
          {selectedProjectId || 'telco-churn-2018'}
        </span>
        <Icon name="chev-right" size={10} style={{ color: 'var(--fg-5)' }}/>
        <span style={{ fontSize: 13, color: 'var(--fg-1)', fontWeight: 500, whiteSpace: 'nowrap' }}>{title}</span>
        <span style={{ fontSize: 11, color: 'var(--fg-4)', marginLeft: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sub}</span>
      </div>

      <div style={{ flex: 1 }}/>

      {/* Search */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '5px 9px',
        width: 280, flexShrink: 0,
        background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 5, color: 'var(--fg-3)',
      }}>
        <Icon name="search" size={13}/>
        <span style={{ fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          Search models, predictions, IDs…
        </span>
        <span className="kbd" style={{ marginLeft: 'auto', flexShrink: 0 }}>⌘K</span>
      </div>

      {/* Env */}
      <Pill tone="ok" icon="circle">prod</Pill>

      {/* Clock */}
      <div className="num" style={{ fontSize: 11, color: 'var(--fg-3)', whiteSpace: 'nowrap' }}>{utc}</div>

      {/* User avatar */}
      <button className="btn btn-ghost btn-sm" style={{ gap: 6 }}>
        <span style={{
          width: 20, height: 20, borderRadius: 999,
          background: 'linear-gradient(135deg, oklch(0.45 0.06 220), oklch(0.30 0.04 220))',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 600,
          color: 'var(--fg-1)', border: '1px solid var(--border-2)',
        }}>AD</span>
        <span>admin</span>
        <Icon name="chev-down" size={10}/>
      </button>
    </header>
  )
}
