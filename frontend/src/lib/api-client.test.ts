import { describe, expect, it } from 'vitest'
import { ApiError, errorMessage } from './api-client'

describe('ApiError', () => {
  it('shows the message the API wrote for the screen', () => {
    const error = new ApiError(404, {
      code: 'not_found',
      message: 'No opportunity 42.',
      fields: [],
    })

    expect(error.message).toBe('No opportunity 42.')
    expect(error.code).toBe('not_found')
  })

  it('keys the rejected inputs by the name the form used', () => {
    const error = new ApiError(422, {
      code: 'invalid_input',
      message: 'Some of what was sent could not be read.',
      fields: [
        { field: 'gross_margin_pct', message: 'Input should be less than or equal to 100' },
        { field: 'business_name', message: 'Field required' },
      ],
    })

    expect(error.fieldErrors()).toEqual({
      gross_margin_pct: 'Input should be less than or equal to 100',
      business_name: 'Field required',
    })
  })

  it('reads a 5xx with no body of ours as the server being unreachable', () => {
    expect(new ApiError(500, undefined).message).toContain('not responding')
  })
})

describe('errorMessage', () => {
  it('tells the user the server is unreachable when the request never landed', () => {
    expect(errorMessage(new TypeError('Failed to fetch'))).toContain('not responding')
  })

  it('falls back for anything it cannot read', () => {
    expect(errorMessage('boom')).toBe('Something went wrong. Try again.')
  })
})
