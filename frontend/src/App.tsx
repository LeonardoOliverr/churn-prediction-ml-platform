import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ModelsPage } from '@/pages/ModelsPage'
import { PredictionsPage } from '@/pages/PredictionsPage'
import { TenantsPage } from '@/pages/TenantsPage'
import { ApiKeysPage } from '@/pages/ApiKeysPage'
import { PredictPage } from '@/pages/PredictPage'
import { HealthPage } from '@/pages/HealthPage'
import { BusinessPage } from '@/pages/BusinessPage'
import { useAuthStore } from '@/store/authStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const jwtToken = useAuthStore((s) => s.jwtToken)
  return jwtToken ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/models" element={<ModelsPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
            <Route path="/predict" element={<PredictPage />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="/tenants" element={<TenantsPage />} />
            <Route path="/keys" element={<ApiKeysPage />} />
            <Route path="/business" element={<BusinessPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
