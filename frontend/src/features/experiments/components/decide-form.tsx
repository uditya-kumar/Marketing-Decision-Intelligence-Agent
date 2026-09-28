import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Eyebrow } from '@/components/common/section'
import { useDecideExperiment } from '../api'

const MIN_REASON = 3

/** Approve or reject a draft (FR-10.2). Approving starts the clock; turning it down asks why,
 *  because that reason is what the decision log has to show next week. */
export function DecideForm({ id }: { id: number }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const approve = useDecideExperiment(id, 'approve')
  const reject = useDecideExperiment(id, 'reject')
  const tooShort = reason.trim().length < MIN_REASON
  const failed = approve.isError || reject.isError

  function submit(event: FormEvent) {
    event.preventDefault()
    if (tooShort) return
    reject.mutate(reason.trim())
  }

  return (
    <div className="flex flex-col gap-2.5 border-t border-hairline pt-5">
      {open ? (
        <form onSubmit={submit} className="flex flex-col gap-2.5">
          <Eyebrow>Why are you turning this down?</Eyebrow>
          <div className="flex items-center gap-3">
            <Input
              autoFocus
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="We're already rotating this creative next week"
              aria-label="Reason for rejecting"
            />
            <Button type="submit" disabled={tooShort || reject.isPending}>
              {reject.isPending ? 'Saving…' : 'Reject'}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <div className="flex items-center gap-4">
          <Button onClick={() => approve.mutate(null)} disabled={approve.isPending}>
            {approve.isPending ? 'Starting…' : 'Approve'}
          </Button>
          <Button variant="outline" onClick={() => setOpen(true)}>
            Reject
          </Button>
          <span className="text-[13px] text-ash">
            Approving records the change; make it on the platform and MDIA watches the metric.
          </span>
        </div>
      )}
      {failed && (
        <p className="text-[13px] text-crimson">
          That didn't save. Try again, or reload if it keeps failing.
        </p>
      )}
    </div>
  )
}
