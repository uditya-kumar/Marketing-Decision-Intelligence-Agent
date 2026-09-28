import { describe, expect, it } from 'vitest'
import {
  formatCount,
  formatDate,
  formatInr,
  formatPercent,
  formatRatio,
  formatShortDate,
} from './format'

describe('formatInr', () => {
  it('groups in lakhs and crores', () => {
    expect(formatInr(600000)).toBe('₹6,00,000')
    expect(formatInr(18419596.69)).toBe('₹1,84,19,597')
    expect(formatInr(428.4)).toBe('₹428')
  })

  it('abbreviates to K, L and Cr when compact', () => {
    expect(formatInr(190000, { compact: true })).toBe('₹1.9L')
    expect(formatInr(24000000, { compact: true })).toBe('₹2.4Cr')
    expect(formatInr(48000, { compact: true })).toBe('₹48K')
    expect(formatInr(1841959.69, { compact: true })).toBe('₹18.4L')
    expect(formatInr(428, { compact: true })).toBe('₹428')
  })

  it('puts the sign before the currency', () => {
    expect(formatInr(-1500)).toBe('−₹1,500')
  })
})

describe('numbers', () => {
  it('formats counts, ratios and percentages', () => {
    expect(formatCount(123456)).toBe('1,23,456')
    expect(formatRatio(4.5917)).toBe('4.6×')
    expect(formatRatio(3)).toBe('3×')
    expect(formatPercent(6.04)).toBe('6%')
    expect(formatPercent(-3.34)).toBe('−3.3%')
  })
})

describe('dates', () => {
  it('formats calendar days without shifting them', () => {
    expect(formatDate('2026-10-14')).toBe('Wed, 14 Oct')
    expect(formatShortDate('2026-04-01')).toBe('1 Apr')
  })
})
