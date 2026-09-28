import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AiBlock } from './ai-block'

describe('AiBlock', () => {
  it('says how many signals the AI words were checked against', () => {
    render(
      <AiBlock eyebrow="Likely cause" grounded signalCount={4}>
        <p>Creative fatigue.</p>
      </AiBlock>,
    )

    expect(screen.getByText('AI · grounded in 4 signals')).toBeTruthy()
  })

  it('reads in the singular for one signal', () => {
    render(
      <AiBlock eyebrow="Likely cause" grounded signalCount={1}>
        <p>Creative fatigue.</p>
      </AiBlock>,
    )

    expect(screen.getByText('AI · grounded in 1 signal')).toBeTruthy()
  })

  it('says no AI answer was used when the rules wrote the words', () => {
    render(
      <AiBlock eyebrow="Likely cause" grounded={false} signalCount={4}>
        <p>CPM rose 23%.</p>
      </AiBlock>,
    )

    expect(screen.getByText('Rule-based · no AI answer used')).toBeTruthy()
    expect(screen.queryByText(/grounded in/)).toBeNull()
  })
})
