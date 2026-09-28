import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Delta } from './delta'

describe('Delta', () => {
  it('colours a rise green only when rising is good for the business', () => {
    const { container } = render(<Delta changePct={12} higherIsBetter={true} />)

    expect(container.firstElementChild?.className).toContain('text-verdant')
    expect(container.textContent).toBe('▲ 12%')
  })

  it('colours a fall green when the metric is a cost', () => {
    const { container } = render(<Delta changePct={-12} higherIsBetter={false} />)

    expect(container.firstElementChild?.className).toContain('text-verdant')
    expect(container.textContent).toBe('▼ 12%')
  })

  it('colours a rise red when rising is bad', () => {
    const { container } = render(<Delta changePct={23} higherIsBetter={false} />)

    expect(container.firstElementChild?.className).toContain('text-crimson')
  })

  it('stays neutral when the direction means neither good nor bad', () => {
    const { container } = render(<Delta changePct={23} higherIsBetter={null} />)

    expect(container.firstElementChild?.className).toContain('text-ash')
  })

  it('shows a flat marker rather than a direction for a movement of nothing', () => {
    const { container } = render(<Delta changePct={0.01} higherIsBetter={true} />)

    expect(container.textContent).toContain('■')
  })

  it('shows a dash when there is nothing to compare against', () => {
    render(<Delta changePct={null} higherIsBetter={true} />)

    expect(screen.getByText('—')).toBeTruthy()
  })
})
