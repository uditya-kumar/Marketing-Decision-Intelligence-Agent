// Display formatting only (UI.md §6): ₹ with Indian grouping, ≤ 1 decimal for %, "Tue, 14 Oct".

const MINUS = '\u2212'
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const COMPACT_UNITS: [number, string][] = [
  [1e7, 'Cr'],
  [1e5, 'L'],
  [1e3, 'K'],
]

const grouped = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

function sign(value: number): string {
  return value < 0 ? MINUS : ''
}

/** Round to at most one decimal and drop a trailing ".0". */
function oneDecimal(value: number): string {
  return String(Math.round(value * 10) / 10)
}

/** ₹6,00,000 in full, or ₹1.9L / ₹2.4Cr / ₹48K when `compact`. */
export function formatInr(value: number, { compact = false } = {}): string {
  const abs = Math.abs(value)
  if (compact) {
    const unit = COMPACT_UNITS.find(([size]) => abs >= size)
    if (unit) return `${sign(value)}₹${oneDecimal(abs / unit[0])}${unit[1]}`
  }
  return `${sign(value)}₹${grouped.format(abs)}`
}

export function formatCount(value: number): string {
  return `${sign(value)}${grouped.format(Math.abs(value))}`
}

/** Ratios such as ROAS and MER: "3.9×". */
export function formatRatio(value: number): string {
  return `${oneDecimal(value)}×`
}

export function formatPercent(value: number): string {
  return `${sign(value)}${oneDecimal(Math.abs(value))}%`
}

/** API dates are ISO calendar days; parse them as local dates so no timezone shifts the day. */
export function parseDate(iso: string): Date {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** "Tue, 14 Oct" */
export function formatDate(iso: string): string {
  const date = parseDate(iso)
  return `${WEEKDAYS[date.getDay()]}, ${formatShortDate(iso)}`
}

/** "14 Oct" */
export function formatShortDate(iso: string): string {
  const date = parseDate(iso)
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`
}

/** "14 Oct, 09:30" for timestamps such as an import time. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  const time = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  return `${date.getDate()} ${MONTHS[date.getMonth()]}, ${time}`
}
