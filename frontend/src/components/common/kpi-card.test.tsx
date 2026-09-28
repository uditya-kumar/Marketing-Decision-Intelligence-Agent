import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KpiCard } from './kpi-card'

const kpi = {
  label: 'ROAS',
  value: '5.11×',
  changePct: 58,
  higherIsBetter: true,
  comparison: 'vs last week',
}

describe('KpiCard', () => {
  it('shows the value, its movement and the goal line', () => {
    const { container } = render(<KpiCard {...kpi} goal="Target 3.5× · on track" />)

    expect(screen.getByText('5.11×')).toBeTruthy()
    expect(container.textContent).toContain('▲ 58%')
    expect(screen.getByText('Target 3.5× · on track')).toBeTruthy()
  })

  it('greys the number out when the data behind it failed a trust check', () => {
    const { container } = render(<KpiCard {...kpi} muted />)

    expect(screen.getByText('5.11×').className).toContain('text-mist')
    // The movement is muted too, so a broken source cannot read as a good week.
    const movement = [...container.querySelectorAll('span')].find(
      (span) => span.textContent === '▲ 58%',
    )
    expect(movement?.className).toContain('text-mist')
  })
})
