import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/lib/api-client'

const keys = {
  status: ['ingestion', 'status'] as const,
  runs: ['ingestion', 'runs'] as const,
  templates: ['ingestion', 'templates'] as const,
}

export function useIngestionStatus() {
  return useQuery({
    queryKey: keys.status,
    queryFn: () => unwrap(api.GET('/api/v1/ingestion/status')),
  })
}

export function useIngestionRuns() {
  return useQuery({
    queryKey: keys.runs,
    queryFn: () => unwrap(api.GET('/api/v1/ingestion/runs', { params: { query: { limit: 20 } } })),
  })
}

export function useTemplates() {
  return useQuery({
    queryKey: keys.templates,
    queryFn: () => unwrap(api.GET('/api/v1/ingestion/templates')),
    staleTime: Infinity,
  })
}

export function useUpload() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData()
      files.forEach((file) => form.append('files', file))
      return unwrap(
        api.POST('/api/v1/ingestion/upload', {
          // OpenAPI types binary uploads as strings; the real payload is the FormData.
          body: { files: files as unknown as string[] },
          bodySerializer: () => form,
        }),
      )
    },
    // New data changes every number on every screen.
    onSuccess: () => queryClient.invalidateQueries(),
  })
}
