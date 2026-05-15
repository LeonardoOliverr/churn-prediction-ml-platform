import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const { jwtToken } = useAuthStore.getState()
  if (jwtToken) {
    config.headers['Authorization'] = `Bearer ${jwtToken}`
  }
  return config
})

export const inferenceClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

inferenceClient.interceptors.request.use((config) => {
  const { apiKey } = useAuthStore.getState()
  if (apiKey) {
    config.headers['x-api-key'] = apiKey
  }
  return config
})
