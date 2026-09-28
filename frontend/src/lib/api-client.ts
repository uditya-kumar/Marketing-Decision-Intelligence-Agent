import createClient from 'openapi-fetch'
import type { components, paths } from '@/types/api'

export type Schemas = components['schemas']

/** Typed client for the MDIA API; paths and payloads come from the generated OpenAPI types. */
export const api = createClient<paths>()

type ErrorBody = Schemas['ErrorOut']

const OFFLINE = 'The server is not responding. Check it is running and try again.'
const FALLBACK = 'Something went wrong. Try again.'

/** A failed request in the API's one error shape (`ErrorOut`), ready to show or inspect. */
export class ApiError extends Error {
  readonly status: number
  readonly code: ErrorBody['code']
  readonly fields: ErrorBody['fields']

  constructor(status: number, body: ErrorBody | undefined) {
    // The API answers every failure with an ErrorOut, so a 5xx without one came from
    // between us and it — a dev proxy or a gateway with nothing to talk to.
    super(body?.message || (status >= 500 ? OFFLINE : FALLBACK))
    this.status = status
    this.code = body?.code ?? 'server_error'
    this.fields = body?.fields ?? []
  }

  /** The invalid inputs keyed by the name the form used for them. */
  fieldErrors(): Record<string, string> {
    return Object.fromEntries(this.fields.map(({ field, message }) => [field, message]))
  }
}

/** Return the response data, or throw an `ApiError` so TanStack Query sees a failure. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request
  if (!response.ok || data === undefined) {
    throw new ApiError(response.status, error as ErrorBody | undefined)
  }
  return data
}

/** A sentence to show for any failure, including the ones that never reached the API. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  // openapi-fetch passes a transport failure straight through, so an unreachable
  // server arrives here as a TypeError rather than as a response we can read.
  if (error instanceof TypeError) return OFFLINE
  return FALLBACK
}
