import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '@/lib/api-client'

/** Every decision, newest first, with the opportunity and experiment behind it (FR-10.4). */
export function useDecisions() {
  return useQuery({
    queryKey: ['decisions'],
    queryFn: () => unwrap(api.GET('/api/v1/decisions')),
    select: (data) => data.decisions,
  })
}
