import { useSyncExternalStore } from 'react'
import { CircleAlert, X } from 'lucide-react'
import { dismiss, snapshot, subscribe } from '@/lib/toast'

/** Where failures from writes are announced; one stack, bottom right, never modal. */
export function Toaster() {
  const toasts = useSyncExternalStore(subscribe, snapshot, snapshot)

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed right-6 bottom-6 z-50 flex w-[360px] flex-col gap-2 print:hidden"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="pointer-events-auto flex items-start gap-3 rounded-lg border border-hairline bg-bone px-4 py-3 shadow-popover"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-crimson" aria-hidden />
          <p className="flex-1 text-ink">{toast.message}</p>
          <button
            type="button"
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss"
            className="rounded-sm p-0.5 text-ash transition-colors duration-150 ease-out hover:text-ink"
          >
            <X className="size-3.5" aria-hidden />
          </button>
        </div>
      ))}
    </div>
  )
}
