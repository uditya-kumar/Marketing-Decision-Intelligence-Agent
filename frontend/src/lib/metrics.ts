import type { Schemas } from '@/lib/api-client'
import { formatCount, formatInr, formatPercent, formatRatio } from '@/lib/format'

export type Metric = Schemas['KpiSummaryOut']['metric']

type Kind = 'money' | 'ratio' | 'percent' | 'count'

// `note` is the plain-language gloss the evidence tree shows under the metric (UI.md §1.5).
const METRICS: Record<Metric, { label: string; kind: Kind; note: string }> = {
  store_revenue: { label: 'Revenue', kind: 'money', note: 'Money the store took' },
  spend: { label: 'Spend', kind: 'money', note: 'Money spent on ads' },
  roas: { label: 'ROAS', kind: 'ratio', note: 'Revenue per rupee of ad spend' },
  mer: { label: 'MER', kind: 'ratio', note: 'Store revenue per rupee of ad spend' },
  cpa: { label: 'CPA', kind: 'money', note: 'Cost per purchase' },
  cpc: { label: 'CPC', kind: 'money', note: 'Cost per click' },
  cpm: { label: 'CPM', kind: 'money', note: 'Cost per thousand views' },
  aov: { label: 'AOV', kind: 'money', note: 'Average order value' },
  store_aov: { label: 'Store AOV', kind: 'money', note: 'Average store order value' },
  ctr: { label: 'CTR', kind: 'percent', note: 'People who click' },
  cvr: { label: 'Conversion rate', kind: 'percent', note: 'Clicks that purchase' },
  bounce_rate: { label: 'Bounce rate', kind: 'percent', note: 'Visits that leave at once' },
  atc_rate: { label: 'Add-to-cart rate', kind: 'percent', note: 'Visits that add to cart' },
  checkout_rate: { label: 'Checkout rate', kind: 'percent', note: 'Carts that reach checkout' },
  purchase_rate: { label: 'Purchase rate', kind: 'percent', note: 'Checkouts that pay' },
  web_cvr: { label: 'Site conversion rate', kind: 'percent', note: 'Visits that purchase' },
  frequency: { label: 'Frequency', kind: 'ratio', note: 'Times each person saw the ad' },
  impressions: { label: 'Impressions', kind: 'count', note: 'Times the ads were shown' },
  clicks: { label: 'Clicks', kind: 'count', note: 'Clicks on the ads' },
  platform_conversions: {
    label: 'Conversions',
    kind: 'count',
    note: 'Purchases the platform reports',
  },
  platform_revenue: {
    label: 'Platform revenue',
    kind: 'money',
    note: 'Revenue the platform reports',
  },
  store_orders: { label: 'Orders', kind: 'count', note: 'Orders the store recorded' },
}

export function metricLabel(metric: Metric): string {
  return METRICS[metric].label
}

/** "Cost per purchase": what the metric means, for readers who don't know the acronym. */
export function metricNote(metric: Metric): string {
  return METRICS[metric].note
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
