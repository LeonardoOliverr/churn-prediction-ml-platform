import { apiClient } from './api'
import type {
  TenantCreate,
  TenantResponse,
  ProjectCreate,
  ProjectResponse,
  ApiKeyCreate,
  ApiKeyResponse,
  ApiKeyRecord,
  ProjectModelConfigListResponse,
  ProjectModelConfigResponse,
  ChampionModelConfigure,
  ChallengerModelConfigure,
  ModelPromotionRequest,
  ModelDeactivationRequest,
} from '@/types/api'

// ── Tenants ───────────────────────────────────────────────────────────────────

export async function createTenant(payload: TenantCreate): Promise<TenantResponse> {
  const { data } = await apiClient.post<TenantResponse>('/admin/tenants', payload)
  return data
}

// ── Projects ──────────────────────────────────────────────────────────────────

export async function createProject(payload: ProjectCreate): Promise<ProjectResponse> {
  const { data } = await apiClient.post<ProjectResponse>('/admin/projects', payload)
  return data
}

// ── API Keys ──────────────────────────────────────────────────────────────────

export async function createApiKey(payload: ApiKeyCreate): Promise<ApiKeyResponse> {
  const { data } = await apiClient.post<ApiKeyResponse>('/admin/keys', payload)
  return data
}

export async function revokeApiKey(keyId: string): Promise<void> {
  await apiClient.delete(`/admin/keys/${keyId}`)
}

export async function listApiKeys(tenantId: string): Promise<ApiKeyRecord[]> {
  const { data } = await apiClient.get<ApiKeyRecord[]>(`/admin/tenants/${tenantId}/keys`)
  return data
}

// ── Model Config ──────────────────────────────────────────────────────────────

export async function listModelConfig(
  tenantId: string,
  projectId?: string | null,
): Promise<ProjectModelConfigListResponse> {
  const params = projectId ? { project_id: projectId } : {}
  const { data } = await apiClient.get<ProjectModelConfigListResponse>(
    `/admin/tenants/${tenantId}/models/config`,
    { params },
  )
  return data
}

export async function configureChampion(
  tenantId: string,
  payload: ChampionModelConfigure,
  projectId?: string | null,
): Promise<ProjectModelConfigResponse> {
  const params = projectId ? { project_id: projectId } : {}
  const { data } = await apiClient.post<ProjectModelConfigResponse>(
    `/admin/tenants/${tenantId}/models/champion`,
    payload,
    { params },
  )
  return data
}

export async function configureChallenger(
  tenantId: string,
  payload: ChallengerModelConfigure,
  projectId?: string | null,
): Promise<ProjectModelConfigResponse> {
  const params = projectId ? { project_id: projectId } : {}
  const { data } = await apiClient.post<ProjectModelConfigResponse>(
    `/admin/tenants/${tenantId}/models/challenger`,
    payload,
    { params },
  )
  return data
}

export async function promoteChallenger(
  tenantId: string,
  modelId: string,
  payload: ModelPromotionRequest,
  projectId?: string | null,
): Promise<ProjectModelConfigResponse> {
  const params = projectId ? { project_id: projectId } : {}
  const { data } = await apiClient.post<ProjectModelConfigResponse>(
    `/admin/tenants/${tenantId}/models/${modelId}/promote`,
    payload,
    { params },
  )
  return data
}

export async function deactivateModel(
  tenantId: string,
  modelId: string,
  payload: ModelDeactivationRequest,
  projectId?: string | null,
): Promise<ProjectModelConfigResponse> {
  const params = projectId ? { project_id: projectId } : {}
  const { data } = await apiClient.post<ProjectModelConfigResponse>(
    `/admin/tenants/${tenantId}/models/${modelId}/deactivate`,
    payload,
    { params },
  )
  return data
}
