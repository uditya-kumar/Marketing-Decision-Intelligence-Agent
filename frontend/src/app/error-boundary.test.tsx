import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './error-boundary'

function Crash(): never {
  throw new Error('rendered nonsense')
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React logs the caught error itself; the test does not need it in the output.
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the screen when nothing goes wrong', () => {
    render(
      <ErrorBoundary>
        <p>Today</p>
      </ErrorBoundary>,
    )

    expect(screen.getByText('Today')).toBeTruthy()
  })

  it('shows a message and a way out instead of a blank page', () => {
    render(
      <ErrorBoundary>
        <Crash />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert').textContent).toContain('This screen ran into a problem.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy()
  })
})
