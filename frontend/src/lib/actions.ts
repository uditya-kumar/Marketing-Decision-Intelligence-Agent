// Display names for the action catalogue (FR-9.1); the action itself is chosen in the backend.
import type { Schemas } from '@/lib/api-client'

export type Action = Schemas['RecommendationOut']['action']

const ACTIONS: Record<Action, string> = {
  pause_creative: 'Pause this creative',
  rotate_creative: 'Rotate in a fresh creative for the same audience',
  refine_audience: 'Narrow the audience',
  investigate_landing_page: 'Check the landing page for this traffic',
  fix_tracking: 'Fix the tracking before acting on these numbers',
  shift_budget: 'Move budget towards what is working',
  adjust_pacing: 'Adjust the daily spend',
}

// The same catalogue named in two words, for the lines that have no room for a sentence:
// the Today strip and the decision log (UI.md §5.1, §5.5).
const NAMES: Record<Action, string> = {
  pause_creative: 'Creative pause',
  rotate_creative: 'Creative rotation',
  refine_audience: 'Audience change',
  investigate_landing_page: 'Landing page check',
  fix_tracking: 'Tracking fix',
  shift_budget: 'Budget shift',
  adjust_pacing: 'Pacing change',
}

export function actionLabel(action: Action): string {
  return ACTIONS[action]
}

export function actionName(action: Action): string {
  return NAMES[action]
}
