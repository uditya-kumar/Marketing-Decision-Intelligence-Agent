import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '@/lib/api-client'

export function useToday() {
  return useQuery({
    queryKey: ['today'],
    queryFn: () => unwrap(api.GET('/api/v1/today')),
  })
}
