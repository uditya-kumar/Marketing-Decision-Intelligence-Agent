import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from 'react'
import { beforeEach, describe, expect, it } from 'vitest'
import { dismiss, snapshot, toast } from '@/lib/toast'
import { Toaster } from './toaster'

describe('Toaster', () => {
  // The store outlives the component, so each test starts with an empty stack.
  beforeEach(() => {
    for (const open of snapshot()) dismiss(open.id)
  })

  it('shows a failure raised from outside React', () => {
    render(<Toaster />)

    act(() => toast('The server is not responding.'))

    expect(screen.getByText('The server is not responding.')).toBeTruthy()
  })

  it('does not stack the same failure twice', () => {
    render(<Toaster />)

    act(() => toast('That did not save.'))
    act(() => toast('That did not save.'))

    expect(screen.getAllByText('That did not save.')).toHaveLength(1)
  })

  it('can be dismissed', async () => {
    render(<Toaster />)
    act(() => toast('Something went wrong.'))

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }))

    expect(screen.queryByText('Something went wrong.')).toBeNull()
  })
})
