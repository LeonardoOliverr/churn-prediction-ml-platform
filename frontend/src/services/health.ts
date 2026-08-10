import axios from 'axios'
import type { HealthResponse, HealthReadyResponse } from '@/types/api'

const base = axios.create({ baseURL: '/api' })

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await base.get<HealthResponse>('/health')
  return data
}

export async function fetchHealthReady(): Promise<HealthReadyResponse> {
  const { data } = await base.get<HealthReadyResponse>('/health/ready')
  return data
}
