import { Checkbox } from '@/components/ui/checkbox'
import type { Schemas } from '@/lib/api-client'
import { CHANNELS } from '../form'

type ProtectedCampaignsProps = {
  campaigns: Schemas['CampaignOut'][]
  selected: number[]
  onChange: (ids: number[]) => void
  error?: string
}

const CHANNEL_LABELS: Record<string, string> = Object.fromEntries(
  CHANNELS.map(({ id, label }) => [id, label]),
)

export function ProtectedCampaigns({
  campaigns,
  selected,
  onChange,
  error,
}: ProtectedCampaignsProps) {
  if (campaigns.length === 0) {
    return (
      <p className="py-[18px] text-[13px] text-ash">
        Your campaigns appear here after the first ad upload.
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-1 py-[18px]">
      <ul className="grid grid-cols-2 gap-x-8 gap-y-3">
        {campaigns.map((campaign) => {
          const id = `campaign-${campaign.id}`
          return (
            <li key={campaign.id} className="flex items-start gap-2.5">
              <Checkbox
                id={id}
                className="mt-0.5"
                checked={selected.includes(campaign.id)}
                onCheckedChange={(checked) =>
                  onChange(
                    checked === true
                      ? [...selected, campaign.id]
                      : selected.filter((c) => c !== campaign.id),
                  )
                }
              />
              <label htmlFor={id} className="flex flex-col">
                <span className="text-ink">{campaign.name}</span>
                <span className="text-[12px] text-ash">{CHANNEL_LABELS[campaign.channel_id]}</span>
              </label>
            </li>
          )
        })}
      </ul>
      {error && <p className="pt-2 text-[13px] text-crimson">{error}</p>}
    </div>
  )
}
