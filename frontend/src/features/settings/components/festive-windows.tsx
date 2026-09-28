import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Schemas } from '@/lib/api-client'
import { INPUT_CLASS } from './field-row'

type FestiveWindow = Schemas['FestiveWindow']

type FestiveWindowsProps = {
  windows: FestiveWindow[]
  onChange: (windows: FestiveWindow[]) => void
  error?: string
}

export function FestiveWindows({ windows, onChange, error }: FestiveWindowsProps) {
  function update(index: number, change: Partial<FestiveWindow>) {
    onChange(windows.map((w, i) => (i === index ? { ...w, ...change } : w)))
  }

  return (
    <div className="flex flex-col gap-3 py-[18px]">
      {windows.length === 0 && (
        <p className="text-[13px] text-ash">None yet. Add Diwali, Navratri or your own sales.</p>
      )}
      {windows.map((window, index) => (
        <div key={index} className="flex items-center gap-3">
          <Input
            aria-label="Name"
            placeholder="Diwali"
            required
            value={window.name}
            onChange={(e) => update(index, { name: e.target.value })}
            className={`${INPUT_CLASS} flex-1`}
          />
          <Input
            aria-label="Start date"
            type="date"
            required
            value={window.start}
            onChange={(e) => update(index, { start: e.target.value })}
            className={`${INPUT_CLASS} w-44`}
          />
          <span className="text-ash">to</span>
          <Input
            aria-label="End date"
            type="date"
            required
            value={window.end}
            onChange={(e) => update(index, { end: e.target.value })}
            className={`${INPUT_CLASS} w-44`}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={`Remove ${window.name || 'window'}`}
            onClick={() => onChange(windows.filter((_, i) => i !== index))}
          >
            <X aria-hidden />
          </Button>
        </div>
      ))}
      {error && <p className="text-[13px] text-crimson">{error}</p>}
      <div>
        <Button
          type="button"
          variant="ghost"
          onClick={() => onChange([...windows, { name: '', start: '', end: '' }])}
        >
          <Plus aria-hidden />
          Add window
        </Button>
      </div>
    </div>
  )
}
