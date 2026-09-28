// Wording for data-trust results, shared by Today and Data. Every number comes from the API.
import type { Schemas } from '@/lib/api-client'
import { formatPercent, formatShortDate } from '@/lib/format'

type SourceTrust = Schemas['SourceTrustOut']
type Source = SourceTrust['source']

export type TrustTone = 'ok' | 'stale' | 'warning' | 'broken' | 'empty'

export type TrustSummary = {
  tone: TrustTone
  label: string
  note?: string
}

const SHORT_NAMES: Record<Source, string> = {
  google_ads: 'Google',
  meta_ads: 'Meta',
  web_analytics: 'Web analytics',
  store_orders: 'Store orders',
}

// What each ad platform calls the conversions it reports.
const CONVERSION_WORDS: Partial<Record<Source, string>> = {
  google_ads: 'conversions',
  meta_ads: 'purchases',
}

export function shortName(source: Source): string {
  return SHORT_NAMES[source]
}

export function conversionWord(source: Source): string {
  return CONVERSION_WORDS[source] ?? 'conversions'
}

export function dayCount(days: number): string {
  return `${days} ${days === 1 ? 'day' : 'days'}`
}

/** "−82%" / "+3%": a change with its sign. */
export function signedPercent(value: number): string {
  return value > 0 ? `+${formatPercent(value)}` : formatPercent(value)
}

/** The badge and short note for one source, worst problem first. */
export function trustSummary(source: SourceTrust): TrustSummary {
  const { freshness, tracking } = source
  if (freshness.last_date === null) return { tone: 'empty', label: 'No data yet' }
  if (tracking && tracking.status !== 'ok') {
    const word = conversionWord(source.source)
    const change =
      tracking.conversions_change_pct === null
        ? ''
        : ` ${signedPercent(tracking.conversions_change_pct)}`
    const since = tracking.since ? ` since ${formatShortDate(tracking.since)}` : ''
    return {
      tone: tracking.status,
      label: tracking.status === 'broken' ? 'Broken' : 'Check tracking',
      note: `${word[0].toUpperCase()}${word.slice(1)}${change} vs store orders${since}`,
    }
  }
  if (freshness.days_behind > 0) {
    return { tone: 'stale', label: 'Stale', note: `${dayCount(freshness.days_behind)} behind` }
  }
  if (freshness.missing_dates.length > 0) {
    return {
      tone: 'warning',
      label: 'Gaps',
      note: `${dayCount(freshness.missing_dates.length)} missing`,
    }
  }
  return { tone: 'ok', label: 'OK' }
}
