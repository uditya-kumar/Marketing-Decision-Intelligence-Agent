/** A one-line failure notice, announced from anywhere — including outside React.
 *
 * Kept as a module store rather than context so the query client's `MutationCache`
 * can raise a toast without a component in between.
 */

export type Toast = { id: number; message: string }

/** Long enough to read a sentence, short enough not to sit on the screen. */
const LIFETIME_MS = 6000

let toasts: Toast[] = []
let nextId = 1
const listeners = new Set<(toasts: Toast[]) => void>()

function publish(next: Toast[]): void {
  toasts = next
  for (const listener of listeners) listener(toasts)
}

export function subscribe(listener: (toasts: Toast[]) => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function snapshot(): Toast[] {
  return toasts
}

export function dismiss(id: number): void {
  publish(toasts.filter((toast) => toast.id !== id))
}

export function toast(message: string): void {
  const id = nextId++
  // The same message twice in a row is one fact, not two notices.
  publish([...toasts.filter((existing) => existing.message !== message), { id, message }])
  setTimeout(() => dismiss(id), LIFETIME_MS)
}
