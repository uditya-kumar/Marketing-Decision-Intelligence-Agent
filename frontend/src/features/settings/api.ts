import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap, type Schemas } from '@/lib/api-client'

const keys = {
  settings: ['settings'] as const,
  campaigns: ['settings', 'campaigns'] as const,
}

export function useSettings() {
  return useQuery({
    queryKey: keys.settings,
    queryFn: () => unwrap(api.GET('/api/v1/settings')),
  })
}

export function useCampaigns() {
  return useQuery({
    queryKey: keys.campaigns,
    queryFn: () => unwrap(api.GET('/api/v1/settings/campaigns')),
  })
}

export function useSaveSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (values: Schemas['SettingsIn']) =>
      unwrap(api.PUT('/api/v1/settings', { body: values })),
    onSuccess: (saved) => {
      queryClient.setQueryData(keys.settings, saved)
      // Goals feed the Today strip.
      return queryClient.invalidateQueries({ queryKey: ['today'] })
    },
  })
}
