import { Link } from 'react-router-dom'
import { ArrowRight, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type TrustBannerProps = {
  title: string
  body: string
}

/** Shown above the KPIs whenever a source fails a trust check (UI.md §5.1). */
export function TrustBanner({ title, body }: TrustBannerProps) {
  return (
    <section
      role="alert"
      className="flex items-center gap-3.5 rounded-sm border border-hairline bg-bone px-5 py-4"
    >
      <TriangleAlert className="size-[18px] shrink-0 text-amber" aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="text-body-sm font-medium text-ink">{title}</p>
        <p className="text-[13px] text-ash">{body}</p>
      </div>
      <Button variant="ghost" asChild>
        <Link to="/data">
          See details
          <ArrowRight aria-hidden />
        </Link>
      </Button>
    </section>
  )
}
