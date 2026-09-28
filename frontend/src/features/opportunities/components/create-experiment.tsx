import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useCreateExperiment } from '../api'

/** "Create experiment" (UI.md §5.2): fills the form in the backend, then shows it for approval. */
export function CreateExperiment({ id }: { id: number }) {
  const navigate = useNavigate()
  const create = useCreateExperiment(id)

  return (
    <div className="flex flex-col gap-2">
      <Button
        onClick={() => create.mutate(undefined, { onSuccess: () => void navigate('/experiments') })}
        disabled={create.isPending}
      >
        {create.isPending ? 'Creating…' : 'Create experiment'}
      </Button>
      {create.isError && (
        <p className="text-[13px] text-crimson">
          We couldn't start an experiment for this one. Try again in a moment.
        </p>
      )}
    </div>
  )
}
