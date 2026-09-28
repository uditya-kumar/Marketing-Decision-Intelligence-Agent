import { Route, Routes } from 'react-router-dom'
import AppLayout from './app-layout'
import OnboardingPage from '@/features/onboarding/page'
import TodayPage from '@/features/today/page'
import OpportunitiesPage from '@/features/opportunities/page'
import PlanPage from '@/features/plan/page'
import ExperimentsPage from '@/features/experiments/page'
import ReportsPage from '@/features/reports/page'
import DecisionsPage from '@/features/decisions/page'
import DataPage from '@/features/data/page'
import SettingsPage from '@/features/settings/page'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<TodayPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="opportunities" element={<OpportunitiesPage />} />
        <Route path="plan" element={<PlanPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="decisions" element={<DecisionsPage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
