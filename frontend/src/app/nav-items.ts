import { Database, FileText, FlaskConical, History, LayoutList, Settings, Sun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type NavItem = {
  label: string
  to: string
  icon: LucideIcon
}

/** Primary navigation (UI.md §2). */
export const primaryNav: NavItem[] = [
  { label: 'Today', to: '/', icon: Sun },
  { label: 'Opportunities', to: '/opportunities', icon: LayoutList },
  { label: 'Experiments', to: '/experiments', icon: FlaskConical },
  { label: 'Decisions', to: '/decisions', icon: History },
  { label: 'Reports', to: '/reports', icon: FileText },
]

/** Secondary navigation, visually separated below the primary group. */
export const secondaryNav: NavItem[] = [
  { label: 'Data', to: '/data', icon: Database },
  { label: 'Settings', to: '/settings', icon: Settings },
]
