import { inferenceClient } from './api'
import type {
  CustomerFeatures,
  PredictResponse,
  BatchPredictRequest,
  BatchPredictResponse,
  PredictionsListResponse,
} from '@/types/api'

export async function predictSingle(features: CustomerFeatures): Promise<PredictResponse> {
  const { data } = await inferenceClient.post<PredictResponse>('/predict', features)
  return data
}

export async function predictBatch(customers: CustomerFeatures[]): Promise<BatchPredictResponse> {
  const payload: BatchPredictRequest = { customers }
  const { data } = await inferenceClient.post<BatchPredictResponse>('/predict/batch', payload)
  return data
}

export async function fetchPredictions(
  page = 1,
  pageSize = 20,
): Promise<PredictionsListResponse> {
  const { data } = await inferenceClient.get<PredictionsListResponse>('/predictions', {
    params: { page, page_size: pageSize },
  })
  return data
}
