import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/lib/api-client'

const KEY = ['experiments']

/** Every experiment with the opportunity it came from; the tabs split them in the browser. */
export function useExperiments() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => unwrap(api.GET('/api/v1/experiments')),
    select: (data) => data.experiments,
  })
}

type Decision = 'approve' | 'reject'

/** Approve or reject a draft. Both move the opportunity too, so its lists refresh. */
export function useDecideExperiment(id: number, decision: Decision) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (reason: string | null) => {
      const options = { params: { path: { experiment_id: id } }, body: { reason } }
      return unwrap(
        decision === 'approve'
          ? api.POST('/api/v1/experiments/{experiment_id}/approve', options)
          : api.POST('/api/v1/experiments/{experiment_id}/reject', options),
      )
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: KEY })
      void client.invalidateQueries({ queryKey: ['opportunities'] })
      void client.invalidateQueries({ queryKey: ['decisions'] })
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}
