import { useState, type FormEvent, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Eyebrow } from '@/components/common/section'
import { useDismissOpportunity } from '../api'

const MIN_REASON = 3

type DismissFormProps = {
  id: number
  defaultOpen?: boolean
  /** The other call on this row, which UI.md §5.2 puts first: Create experiment. */
  primary?: ReactNode
}

/** Dismissing needs a reason: it goes in the decision log, and the detectors learn from it. */
export function DismissForm({ id, defaultOpen = false, primary }: DismissFormProps) {
  const [open, setOpen] = useState(defaultOpen)
  const [reason, setReason] = useState('')
  const dismiss = useDismissOpportunity(id)
  const tooShort = reason.trim().length < MIN_REASON

  if (!open) {
    return (
      <div className="flex items-center gap-4 border-t border-hairline pt-5">
        {primary}
        <Button variant="outline" onClick={() => setOpen(true)}>
          Dismiss
        </Button>
        <span className="text-[13px] text-ash">
          Not worth acting on? Say why and it stops coming back.
        </span>
      </div>
    )
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (tooShort) return
    dismiss.mutate(reason.trim())
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2.5 border-t border-hairline pt-5">
      <Eyebrow>Why are you dismissing this?</Eyebrow>
      <div className="flex items-center gap-3">
        <Input
          autoFocus
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Seasonal sale, we expected this"
          aria-label="Reason for dismissing"
        />
        <Button type="submit" disabled={tooShort || dismiss.isPending}>
          {dismiss.isPending ? 'Dismissing…' : 'Dismiss'}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
