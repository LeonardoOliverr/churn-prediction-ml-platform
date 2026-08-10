import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@/components/primitives'
import { TenantSelector } from './TenantSelector'

type NavItemProps = { icon: string; label: string; active: boolean; badge?: { label: string | number; tone: string } | null; onClick: () => void }
function NavItem({ icon, label, active, badge, onClick }: NavItemProps) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 10,
      width: '100%', padding: '7px 10px', borderRadius: 4,
      background: active ? 'var(--bg-3)' : 'transparent',
      border: '1px solid', borderColor: active ? 'var(--border-2)' : 'transparent',
      color: active ? 'var(--fg-1)' : 'var(--fg-2)',
      fontSize: 13, cursor: 'pointer', textAlign: 'left',
      fontFamily: 'inherit', position: 'relative',
      transition: 'background 80ms ease, color 80ms ease',
    }}
      onMouseEnter={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = 'var(--bg-3)'; (e.currentTarget as HTMLElement).style.color = 'var(--fg-1)' } }}
      onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--fg-2)' } }}
    >
      {active && <span style={{ position: 'absolute', left: -10, top: 6, bottom: 6, width: 2, background: 'var(--accent-fg)', borderRadius: 999 }}/>}
      <Icon name={icon} size={15} strokeWidth={1.6}/>
      <span style={{ flex: 1 }}>{label}</span>
      {badge && (
        <span className="num" style={{
          fontSize: 10, padding: '1px 5px', borderRadius: 3,
          background: badge.tone === 'amber' ? 'var(--warn-soft)' : badge.tone === 'crit' ? 'var(--crit-soft)' : 'var(--bg-4)',
          color: badge.tone === 'amber' ? 'var(--warn-fg)' : badge.tone === 'crit' ? 'var(--crit-fg)' : 'var(--fg-2)',
          border: `1px solid ${badge.tone === 'amber' ? 'var(--warn-line)' : badge.tone === 'crit' ? 'var(--crit-line)' : 'var(--border-1)'}`,
        }}>{badge.label}</span>
      )}
    </button>
  )
}

const SECTIONS = [
  { title: 'Operations', items: [
    { id: '/dashboard',   icon: 'grid',      label: 'Dashboard' },
    { id: '/business',    icon: 'briefcase', label: 'Business' },
    { id: '/models',      icon: 'models',    label: 'Models' },
    { id: '/predict',     icon: 'predict',   label: 'Predict' },
    { id: '/predictions', icon: 'logs',      label: 'Predictions' },
  ]},
  { title: 'Platform', items: [
    { id: '/health',    icon: 'health',   label: 'Health' },
    { id: '/api-keys',  icon: 'key',      label: 'API Keys' },
    { id: '/tenants',   icon: 'tenants',  label: 'Tenants' },
  ]},
]

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <aside style={{
      width: 'var(--sidebar-w)', minWidth: 'var(--sidebar-w)',
      background: 'var(--bg-1)', borderRight: '1px solid var(--border-1)',
      display: 'flex', flexDirection: 'column', height: '100%',
    }}>
      {/* Brand */}
      <div style={{ padding: '14px 16px 10px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 24, height: 24, borderRadius: 5,
          background: 'linear-gradient(135deg, oklch(0.40 0.06 220), oklch(0.30 0.04 220))',
          border: '1px solid var(--border-2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-fg)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 18l5-12 3 7 3-4 5 9"/>
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--fg-1)' }}>Tarpon</div>
          <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--fg-4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 1 }}>
            Control Plane · v2.7
          </div>
        </div>
      </div>

      {/* Tenant selector */}
      <div style={{ padding: '0 12px 12px' }}>
        <TenantSelector/>
      </div>

      {/* Nav sections */}
      <nav style={{ flex: 1, padding: '0 12px 12px', overflow: 'auto' }}>
        {SECTIONS.map((sec, si) => (
          <div key={sec.title} style={{ marginTop: si === 0 ? 0 : 18 }}>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 10px 6px', fontWeight: 500 }}>
              {sec.title}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {sec.items.map(it => (
                <NavItem key={it.id} icon={it.icon} label={it.label}
                  active={location.pathname === it.id || (it.id !== '/' && location.pathname.startsWith(it.id))}
                  badge={null}
                  onClick={() => navigate(it.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer status */}
      <div style={{ borderTop: '1px solid var(--border-1)', padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--fg-3)', whiteSpace: 'nowrap' }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--ok)', boxShadow: '0 0 6px var(--ok)', display: 'inline-block' }} className="pulse-dot"/>
            <span>Control plane</span>
          </div>
          <span className="num" style={{ color: 'var(--fg-2)', fontSize: 11, whiteSpace: 'nowrap' }}>1 region</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, gap: 8 }}>
          <span style={{ color: 'var(--fg-3)', whiteSpace: 'nowrap' }}>Build</span>
          <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10, whiteSpace: 'nowrap' }}>1.0.0 · local</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, gap: 8 }}>
          <span style={{ color: 'var(--fg-3)' }}>Operator</span>
          <span style={{ color: 'var(--fg-2)', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <Icon name="user" size={11}/> admin
          </span>
        </div>
      </div>
    </aside>
  )
}
