import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function AppLayout() {
  const location = useLocation()
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: 'var(--bg-0)' }}>
      <Sidebar/>
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
        <Topbar/>
        <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg-0)' }}>
          <div key={location.pathname} className="fade-in">
            <Outlet/>
          </div>
        </main>
      </div>
    </div>
  )
}
