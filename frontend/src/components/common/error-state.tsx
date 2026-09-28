import { CircleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type ErrorStateProps = {
  message?: string
  onRetry: () => void
}

export function ErrorState({ message = "We couldn't load this.", onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex items-center gap-3 rounded-lg border border-hairline bg-bone px-5 py-4"
    >
      <CircleAlert className="size-4 shrink-0 text-crimson" aria-hidden />
      <p className="flex-1 text-ink">{message}</p>
      <Button variant="secondary" onClick={onRetry}>
        Try again
      </Button>
    </div>
  )
}
