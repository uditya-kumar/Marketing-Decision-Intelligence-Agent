import { Route, Routes } from 'react-router-dom'
import AppLayout from './app-layout'
import TodayPage from '@/features/today/page'
import OpportunitiesPage from '@/features/opportunities/page'
import OpportunityDetailPage from '@/features/opportunities/detail-page'
import ExperimentsPage from '@/features/experiments/page'
import DecisionsPage from '@/features/decisions/page'
import ReportsPage from '@/features/reports/page'
import DataPage from '@/features/data/page'
import SettingsPage from '@/features/settings/page'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<TodayPage />} />
        <Route path="opportunities" element={<OpportunitiesPage />} />
        <Route path="opportunities/:id" element={<OpportunityDetailPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="decisions" element={<DecisionsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
