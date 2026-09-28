import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import { useCampaigns, useSettings } from './api'
import { ComputedPanel } from './components/computed-panel'
import { SettingsForm } from './components/settings-form'

export default function SettingsPage() {
  const settings = useSettings()
  const campaigns = useCampaigns()

  if (settings.isError || campaigns.isError) {
    const retry = () => {
      void settings.refetch()
      void campaigns.refetch()
    }
    return <ErrorState message="We couldn't load your settings." onRetry={retry} />
  }
  if (!settings.data || !campaigns.data) {
    return (
      <>
        <Skeleton className="h-24 w-2/3" />
        <div className="flex gap-10">
          <Skeleton className="h-[480px] flex-1" />
          <Skeleton className="h-48 w-[300px]" />
        </div>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Settings"
        summary={
          settings.data.configured
            ? 'Your goals and economics. Every number in MDIA is judged against these.'
            : 'Start with your margin and goals, so MDIA can tell good weeks from bad ones.'
        }
      />
      <div className="flex items-start gap-10">
        <SettingsForm saved={settings.data.settings} campaigns={campaigns.data} />
        <ComputedPanel view={settings.data} />
      </div>
    </>
  )
}
