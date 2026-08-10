import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { TenantResponse, ProjectResponse } from '@/types/api'

interface AuthStore {
  jwtToken: string | null
  apiKey: string | null
  knownTenants: TenantResponse[]
  knownProjects: ProjectResponse[]
  selectedTenantId: string | null
  selectedProjectId: string | null

  setJwt: (token: string) => void
  setApiKey: (key: string) => void
  addTenant: (tenant: TenantResponse) => void
  addProject: (project: ProjectResponse) => void
  selectTenant: (id: string) => void
  selectProject: (id: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      jwtToken: null,
      apiKey: null,
      knownTenants: [],
      knownProjects: [],
      selectedTenantId: null,
      selectedProjectId: null,

      setJwt: (token) => set({ jwtToken: token }),
      setApiKey: (key) => set({ apiKey: key }),

      addTenant: (tenant) =>
        set((s) => ({
          knownTenants: s.knownTenants.some((t) => t.id === tenant.id)
            ? s.knownTenants
            : [...s.knownTenants, tenant],
          selectedTenantId: s.selectedTenantId ?? tenant.id,
        })),

      addProject: (project) =>
        set((s) => ({
          knownProjects: s.knownProjects.some((p) => p.id === project.id)
            ? s.knownProjects
            : [...s.knownProjects, project],
        })),

      selectTenant: (id) => set({ selectedTenantId: id, selectedProjectId: null }),
      selectProject: (id) => set({ selectedProjectId: id }),

      logout: () =>
        set({
          jwtToken: null,
          apiKey: null,
          selectedTenantId: null,
          selectedProjectId: null,
        }),
    }),
    {
      name: 'churn-auth',
      partialize: (s) => ({
        jwtToken: s.jwtToken,
        apiKey: s.apiKey,
        knownTenants: s.knownTenants,
        knownProjects: s.knownProjects,
        selectedTenantId: s.selectedTenantId,
        selectedProjectId: s.selectedProjectId,
      }),
    },
  ),
)
