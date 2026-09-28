import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
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
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-muted text-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )
      }
    >
      <Icon className="size-4" aria-hidden />
      {item.label}
    </NavLink>
  )
}

export default function AppLayout() {
  const { pathname } = useLocation()

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border px-3 py-4">
        <div className="px-3 pb-4 text-sm font-semibold">MDIA · NovaWear</div>
        <nav className="flex flex-1 flex-col gap-1">
          {primaryNav.map((item) => (
            <SidebarLink key={item.to} item={item} />
          ))}
          <div className="my-2 border-t border-border" />
          {secondaryNav.map((item) => (
            <SidebarLink key={item.to} item={item} />
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-6 py-3">
          <h2 className="text-base font-semibold">{pageTitle(pathname)}</h2>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Data as of —</span>
            <Button size="sm" variant="outline">
              <Upload className="size-4" aria-hidden />
              Upload
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-auto px-6 py-8">
          <div className="mx-auto w-full max-w-[1120px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
