import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { listApiKeys, createApiKey, revokeApiKey } from '@/services/admin'
import type { ApiKeyCreate } from '@/types/api'

export function useApiKeys() {
  const tenantId = useAuthStore((s) => s.selectedTenantId)

  return useQuery({
    queryKey: ['api-keys', tenantId],
    queryFn: () => listApiKeys(tenantId!),
    enabled: !!tenantId,
    staleTime: 30_000,
  })
}

export function useCreateApiKey() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.selectedTenantId)

  return useMutation({
    mutationFn: (payload: ApiKeyCreate) => createApiKey(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys', tenantId] }),
  })
}

export function useRevokeApiKey() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.selectedTenantId)

  return useMutation({
    mutationFn: (keyId: string) => revokeApiKey(keyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys', tenantId] }),
  })
}
