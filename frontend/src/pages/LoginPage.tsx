import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '@/components/primitives'
import { useAuthStore } from '@/store/authStore'

const STATUS_TILES = [
  { label: 'Control plane',      value: 'operational', tone: 'ok'      },
  { label: 'Inference fleet',    value: '1 node',      tone: 'ok'      },
  { label: 'Predictions / day',  value: '~7k',         tone: 'neutral' },
  { label: 'Active tenants',     value: '—',           tone: 'neutral' },
  { label: 'Active models',      value: '—',           tone: 'neutral' },
  { label: 'Dataset',            value: 'IBM Telco',   tone: 'neutral' },
]

const COMPLIANCE = ['SOC 2', 'ISO 27001', 'HIPAA-ready', 'GDPR']

export function LoginPage() {
  const [method,    setMethod]    = useState<'jwt' | 'apikey'>('jwt')
  const [jwt,       setJwt]       = useState('')
  const [tenantId,  setTenantId]  = useState('')
  const [tenantName,setTenantName]= useState('')
  const [loading,   setLoading]   = useState(false)
  const navigate = useNavigate()
  const { setJwt: storeJwt, addTenant } = useAuthStore()

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    if (!jwt.trim()) return
    setLoading(true)
    storeJwt(jwt.trim())
    if (tenantId.trim()) {
      addTenant({
        id:   tenantId.trim(),
        name: tenantName.trim() || tenantId.trim(),
        slug: tenantName.trim().toLowerCase().replace(/\s+/g, '-') || tenantId.trim(),
      })
    }
    setTimeout(() => { setLoading(false); navigate('/dashboard') }, 400)
  }

  return (
    <div style={{
      height: '100vh', width: '100vw',
      display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 460px',
      background: 'var(--bg-0)', color: 'var(--fg-1)',
    }}>
      {/* Left rail */}
      <div style={{
        background: 'linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%)',
        borderRight: '1px solid var(--border-1)',
        padding: '32px 40px',
        display: 'flex', flexDirection: 'column',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Background grid */}
        <svg style={{ position: 'absolute', inset: 0, opacity: 0.25 }} width="100%" height="100%">
          <defs>
            <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M32 0H0V32" fill="none" stroke="var(--border-1)" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)"/>
        </svg>

        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, position: 'relative' }}>
          <div style={{
            width: 32, height: 32, borderRadius: 6,
            background: 'linear-gradient(135deg, oklch(0.40 0.06 220), oklch(0.28 0.04 220))',
            border: '1px solid var(--border-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-fg)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 18l5-12 3 7 3-4 5 9"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>Tarpon</div>
            <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--fg-4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 1 }}>Control Plane · v2.7</div>
          </div>
        </div>

        {/* Status tiles */}
        <div style={{ marginTop: 60, position: 'relative' }}>
          <div style={{ fontSize: 11, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)', marginBottom: 16 }}>System status</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, maxWidth: 480 }}>
            {STATUS_TILES.map(t => (
              <div key={t.label} style={{ padding: '10px 12px', background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 4 }}>
                <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{t.label}</div>
                <div className="num" style={{ fontSize: 14, color: t.tone === 'ok' ? 'var(--ok-fg)' : 'var(--fg-1)', marginTop: 2 }}>{t.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 'auto', position: 'relative' }}>
          <div style={{ fontSize: 11, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)', lineHeight: 1.5 }}>
            Authorized personnel only. All access is logged and audited.
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 12, fontSize: 11, color: 'var(--fg-4)' }}>
            {COMPLIANCE.map(c => (
              <span key={c} style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                <span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--ok)' }}/>
                {c}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Form panel */}
      <div style={{ padding: '60px 48px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ fontSize: 22, fontWeight: 500, letterSpacing: '-0.01em' }}>Sign in to control plane</div>
        <div style={{ fontSize: 13, color: 'var(--fg-3)', marginTop: 6 }}>
          Paste your admin JWT or use an API key with <span className="mono">keys:manage</span> scope.
        </div>

        {/* Method tabs */}
        <div style={{ display: 'flex', gap: 4, padding: 3, background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 6, marginTop: 24, width: 'fit-content' }}>
          {([['jwt', 'JWT Token'], ['apikey', 'API Key']] as const).map(([id, label]) => (
            <button key={id} onClick={() => setMethod(id)} className="btn btn-sm" style={{
              background:  method === id ? 'var(--bg-3)' : 'transparent',
              borderColor: method === id ? 'var(--border-2)' : 'transparent',
              color:       method === id ? 'var(--fg-1)' : 'var(--fg-3)',
            }}>{label}</button>
          ))}
        </div>

        <form onSubmit={handleSubmit} style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {method === 'jwt' ? (
            <>
              <LoginField label="JWT Token">
                <textarea
                  rows={3}
                  className="input mono"
                  placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                  value={jwt}
                  onChange={e => setJwt(e.target.value)}
                  style={{ resize: 'none', lineHeight: 1.5, paddingTop: 8, paddingBottom: 8 }}
                />
              </LoginField>
              <div style={{ padding: '10px 12px', background: 'var(--bg-3)', border: '1px solid var(--border-1)', borderRadius: 4, fontSize: 11, color: 'var(--fg-4)', display: 'flex', gap: 8 }}>
                <Icon name="info" size={12} style={{ flexShrink: 0, marginTop: 1 }}/>
                <span>Generate externally: <span className="mono" style={{ color: 'var(--fg-2)', fontSize: 10 }}>{'python -c "import jwt; print(jwt.encode({\'sub\':\'admin\'}, \'SECRET\', \'HS256\'))"'}</span></span>
              </div>
              {/* Optional tenant bootstrap */}
              <div style={{ border: '1px dashed var(--border-2)', borderRadius: 4, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Initial tenant (optional)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <LoginField label="Tenant ID (UUID)">
                    <input className="input mono" style={{ fontSize: 11 }} placeholder="xxxxxxxx-xxxx-…"
                      value={tenantId} onChange={e => setTenantId(e.target.value)}/>
                  </LoginField>
                  <LoginField label="Display name">
                    <input className="input" style={{ fontSize: 11 }} placeholder="e.g. IBM Telco"
                      value={tenantName} onChange={e => setTenantName(e.target.value)}/>
                  </LoginField>
                </div>
              </div>
            </>
          ) : (
            <>
              <LoginField label="API Key">
                <input className="input mono" placeholder="churn_live_sk_…"
                  value={jwt} onChange={e => setJwt(e.target.value)}/>
              </LoginField>
              <div style={{ padding: '10px 12px', background: 'var(--warn-soft)', border: '1px solid var(--warn-line)', borderRadius: 4, fontSize: 12, color: 'var(--warn-fg)', display: 'flex', gap: 8 }}>
                <Icon name="alert" size={13}/>
                <span>API key login is for service accounts. Human operators should use JWT.</span>
              </div>
            </>
          )}

          <button type="submit" className="btn btn-primary" style={{ height: 38, justifyContent: 'center', marginTop: 4 }}
            disabled={!jwt.trim() || loading}>
            {loading
              ? <><Icon name="refresh" size={12}/> Authenticating…</>
              : <>Sign in <Icon name="chev-right" size={12}/></>}
          </button>
        </form>

        <div style={{ marginTop: 'auto', paddingTop: 32, fontSize: 11, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)' }}>
          v2.7 · local · IBM Telco Churn Platform
        </div>
      </div>
    </div>
  )
}

function LoginField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 10, color: 'var(--fg-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      {children}
    </div>
  )
}
