import createClient from 'openapi-fetch'
import type { components, paths } from '@/types/api'

export type Schemas = components['schemas']

/** Typed client for the MDIA API; paths and payloads come from the generated OpenAPI types. */
export const api = createClient<paths>()

type FieldError = { loc: (string | number)[]; msg: string }

/** A failed request, with the API's `detail` kept so forms can show field errors. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `Request failed (${status})`)
    this.status = status
    this.detail = detail
  }

  /** Pydantic validation errors keyed by field name (the part of `loc` after "body"). */
  fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.detail)) return {}
    const errors: Record<string, string> = {}
    for (const { loc, msg } of this.detail as FieldError[]) {
      const field = String(loc[1] ?? loc[0])
      errors[field] ??= msg.replace(/^Value error, /, '')
    }
    return errors
  }
}

/** Return the response data, or throw an `ApiError` so TanStack Query sees a failure. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request
  if (!response.ok || data === undefined) {
    const detail = (error as { detail?: unknown } | undefined)?.detail
    throw new ApiError(response.status, detail)
  }
  return data
}
