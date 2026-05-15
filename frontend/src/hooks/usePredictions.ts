import { useQuery } from '@tanstack/react-query'
import { fetchPredictions } from '@/services/predict'

export function usePredictions(page: number, pageSize: number) {
  return useQuery({
    queryKey: ['predictions', page, pageSize],
    queryFn: () => fetchPredictions(page, pageSize),
    staleTime: 15_000,
  })
}
