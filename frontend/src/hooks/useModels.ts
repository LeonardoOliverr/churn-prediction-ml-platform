import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import {
  listModelConfig,
  configureChampion,
  configureChallenger,
  promoteChallenger,
  deactivateModel,
} from '@/services/admin'
import type {
  ChampionModelConfigure,
  ChallengerModelConfigure,
  ModelPromotionRequest,
  ModelDeactivationRequest,
} from '@/types/api'

export function useModelConfig() {
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  return useQuery({
    queryKey: ['model-config', selectedTenantId, selectedProjectId],
    queryFn: () => listModelConfig(selectedTenantId!, selectedProjectId),
    enabled: !!selectedTenantId,
    staleTime: 30_000,
  })
}

export function useConfigureChampion() {
  const qc = useQueryClient()
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  return useMutation({
    mutationFn: (payload: ChampionModelConfigure) =>
      configureChampion(selectedTenantId!, payload, selectedProjectId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['model-config', selectedTenantId, selectedProjectId] }),
  })
}

export function useConfigureChallenger() {
  const qc = useQueryClient()
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  return useMutation({
    mutationFn: (payload: ChallengerModelConfigure) =>
      configureChallenger(selectedTenantId!, payload, selectedProjectId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['model-config', selectedTenantId, selectedProjectId] }),
  })
}

export function usePromoteChallenger() {
  const qc = useQueryClient()
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  return useMutation({
    mutationFn: ({ modelId, payload }: { modelId: string; payload: ModelPromotionRequest }) =>
      promoteChallenger(selectedTenantId!, modelId, payload, selectedProjectId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['model-config', selectedTenantId, selectedProjectId] }),
  })
}

export function useDeactivateModel() {
  const qc = useQueryClient()
  const { selectedTenantId, selectedProjectId } = useAuthStore()

  return useMutation({
    mutationFn: ({ modelId, payload }: { modelId: string; payload: ModelDeactivationRequest }) =>
      deactivateModel(selectedTenantId!, modelId, payload, selectedProjectId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['model-config', selectedTenantId, selectedProjectId] }),
  })
}
