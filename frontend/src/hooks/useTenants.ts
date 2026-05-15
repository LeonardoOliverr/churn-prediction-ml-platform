import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { createTenant, createProject } from '@/services/admin'
import type { TenantCreate, ProjectCreate } from '@/types/api'

export function useCreateTenant() {
  const addTenant = useAuthStore((s) => s.addTenant)

  return useMutation({
    mutationFn: (payload: TenantCreate) => createTenant(payload),
    onSuccess: (tenant) => addTenant(tenant),
  })
}

export function useCreateProject() {
  const addProject = useAuthStore((s) => s.addProject)

  return useMutation({
    mutationFn: (payload: ProjectCreate) => createProject(payload),
    onSuccess: (project) => addProject(project),
  })
}
