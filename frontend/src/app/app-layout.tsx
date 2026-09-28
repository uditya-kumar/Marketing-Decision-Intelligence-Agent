import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useIngestionStatus } from '@/features/data/api'
import { useSettings } from '@/features/settings/api'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { primaryNav, secondaryNav, type NavItem } from './nav-items'

const allNav: NavItem[] = [...primaryNav, ...secondaryNav]

function pageTitle(pathname: string): string {
  const match = allNav.find((item) =>
    item.to === '/' ? pathname === '/' : pathname.startsWith(item.to),
  )
  return match?.label ?? 'MDIA'
}

function SidebarLink({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-ink transition-colors duration-150 ease-out',
          isActive ? 'bg-linen' : 'hover:bg-linen/60',
        )
      }
    >
      <Icon className="size-4 text-ash" aria-hidden />
      {item.label}
    </NavLink>
  )
}

function Brand() {
  const { data } = useSettings()
  const name = data?.settings?.business_name ?? 'MDIA'
  return (
    <div className="flex items-center gap-2.5 px-2.5">
      <span className="flex size-6 items-center justify-center rounded-lg bg-ink text-[13px] text-parchment">
        {name.charAt(0).toUpperCase()}
      </span>
      <span className="flex flex-col">
        <span className="font-medium text-ink">{name}</span>
        <span className="text-[11px] text-ash">Decision Intelligence</span>
      </span>
    </div>
  )
}

function AsOfDate() {
  const { data } = useIngestionStatus()
  const asOf = data?.as_of_date
  return (
    <span className="flex items-center gap-2 font-mono text-[12px] text-ash">
      <span className={cn('size-1.5 rounded-full', asOf ? 'bg-verdant' : 'bg-mist')} aria-hidden />
      {asOf ? `Data as of ${formatDate(asOf)}` : 'No data yet'}
    </span>
  )
}

export default function AppLayout() {
  const { pathname } = useLocation()

  return (
    <div className="flex min-h-svh bg-parchment text-ink">
      <aside className="sticky top-0 flex h-svh w-60 shrink-0 flex-col gap-5 border-r border-hairline bg-bone px-3 py-5">
        <Brand />
        <nav className="flex flex-col gap-0.5">
          {primaryNav.map((item) => (
            <SidebarLink key={item.to} item={item} />
          ))}
          <div className="mx-2.5 my-3 border-t border-hairline" />
          {secondaryNav.map((item) => (
            <SidebarLink key={item.to} item={item} />
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-hairline px-10 py-3.5">
          <span className="text-ink">{pageTitle(pathname)}</span>
          <div className="flex items-center gap-5">
            <AsOfDate />
            <Button variant="secondary" asChild>
              <Link to="/data">
                <Upload aria-hidden />
                Upload
              </Link>
            </Button>
          </div>
        </header>

        <main className="flex-1 px-14 pt-12 pb-16">
          <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-10">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
