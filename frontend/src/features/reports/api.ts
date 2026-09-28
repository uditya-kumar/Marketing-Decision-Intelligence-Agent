import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/lib/api-client'

const KEY = ['reports']

/** Past reports, newest first, plus the week a fresh one would cover (FR-11). */
export function useReports() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => unwrap(api.GET('/api/v1/reports')),
  })
}

/** Write the report for a week; the same week generated twice replaces its report. */
export function useGenerateReport() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (weekEnd: string | null) =>
      unwrap(api.POST('/api/v1/reports/weekly', { body: { week_end: weekEnd } })),
    onSuccess: () => client.invalidateQueries({ queryKey: KEY }),
  })
}
