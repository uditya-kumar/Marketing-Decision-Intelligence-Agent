import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/lib/api-client'
import type { Opportunity } from '@/lib/opportunities'

const KEY = ['opportunities']

/** Every opportunity the last run stored, ranked. The list is short, so the segmented
 *  control filters it in the browser and the counts come for free. */
export function useOpportunities() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => unwrap(api.GET('/api/v1/opportunities')),
    select: (data) => data.opportunities,
  })
}

/** The detail payload as the generated client types it; that type is the one components must
 *  use, because the client widens fixed-length pairs such as `expected_impact`. */
export type OpportunityDetail = NonNullable<ReturnType<typeof useOpportunity>['data']>
export type Recommendation = NonNullable<OpportunityDetail['recommendation']>

export function useOpportunity(id: number) {
  return useQuery({
    queryKey: [...KEY, id],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/opportunities/{opportunity_id}', {
          params: { path: { opportunity_id: id } },
        }),
      ),
  })
}

export function useDismissOpportunity(id: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) =>
      unwrap(
        api.POST('/api/v1/opportunities/{opportunity_id}/dismiss', {
          params: { path: { opportunity_id: id } },
          body: { reason },
        }),
      ),
    // Today counts open opportunities, so it changes too.
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: KEY })
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}

/** Turn the recommended action into an experiment, auto-filled by the backend (FR-10.1).
 *  Asking twice returns the draft that already exists, so the button is safe to press again. */
export function useCreateExperiment(id: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/v1/experiments', { body: { opportunity_id: id } })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['experiments'] })
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}

// The five dimensions `GET /metrics` can break a day down by; the rest are account-wide.
const DIMENSIONS = ['channel', 'campaign', 'ad_set', 'creative', 'age_group'] as const
type Dimension = (typeof DIMENSIONS)[number]

function dimensionOf(level: string): Dimension | null {
  return DIMENSIONS.find((dimension) => dimension === level) ?? null
}

const TREND_DAYS = 30

/** The primary metric per day for this entity, for the charts disclosure. */
export function useOpportunityTrend(row: Opportunity) {
  const dimension = dimensionOf(row.entity_level)
  const query = {
    metric: row.primary_metric,
    dimension,
    days: TREND_DAYS,
    end: row.window.end,
  }
  return useQuery({
    queryKey: ['metrics', query],
    queryFn: () => unwrap(api.GET('/api/v1/metrics', { params: { query } })),
    // "total" is what an account-wide series is called. In a breakdown the opportunity's key
    // carries its channel ("4|25-34"), which the series keys don't, so the name lines up instead.
    select: (data) =>
      (dimension === null
        ? data.series.find((series) => series.key === 'total')
        : data.series.find(
            (series) => series.key === row.entity_key || series.name === row.entity_name,
          )) ?? null,
  })
}
