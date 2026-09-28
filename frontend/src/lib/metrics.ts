import type { Schemas } from '@/lib/api-client'
import { formatCount, formatInr, formatPercent, formatRatio } from '@/lib/format'

export type Metric = Schemas['KpiSummaryOut']['metric']

type Kind = 'money' | 'ratio' | 'percent' | 'count'

const METRICS: Record<Metric, { label: string; kind: Kind }> = {
  store_revenue: { label: 'Revenue', kind: 'money' },
  spend: { label: 'Spend', kind: 'money' },
  roas: { label: 'ROAS', kind: 'ratio' },
  mer: { label: 'MER', kind: 'ratio' },
  cpa: { label: 'CPA', kind: 'money' },
  cpc: { label: 'CPC', kind: 'money' },
  cpm: { label: 'CPM', kind: 'money' },
  aov: { label: 'AOV', kind: 'money' },
  store_aov: { label: 'Store AOV', kind: 'money' },
  ctr: { label: 'CTR', kind: 'percent' },
  cvr: { label: 'Conversion rate', kind: 'percent' },
  bounce_rate: { label: 'Bounce rate', kind: 'percent' },
  frequency: { label: 'Frequency', kind: 'ratio' },
  impressions: { label: 'Impressions', kind: 'count' },
  clicks: { label: 'Clicks', kind: 'count' },
  platform_conversions: { label: 'Conversions', kind: 'count' },
  platform_revenue: { label: 'Platform revenue', kind: 'money' },
  store_orders: { label: 'Orders', kind: 'count' },
}

export function metricLabel(metric: Metric): string {
  return METRICS[metric].label
}

/** Format a metric value for display; `compact` shortens money to ₹1.9L. */
export function formatMetric(metric: Metric, value: number | null, compact = false): string {
  if (value === null) return '—'
  switch (METRICS[metric].kind) {
    case 'money':
      // Per-unit costs stay exact (₹428); totals shorten.
      return formatInr(value, { compact: compact && Math.abs(value) >= 1e4 })
    case 'ratio':
      return formatRatio(value)
    case 'percent':
      // Rates arrive as fractions (clicks / impressions).
      return formatPercent(value * 100)
    case 'count':
      return formatCount(value)
  }
}
