// Row builders for the unit tests. The API shapes are wide and the wording helpers only read
// a few fields, so the tests override what they care about and take these defaults for the rest.
import type { Decision } from '@/lib/decisions'
import type { Experiment } from '@/lib/experiments'
import type { Opportunity } from '@/lib/opportunities'

export function opportunityRow(overrides: Partial<Opportunity> = {}): Opportunity {
  return {
    id: 1,
    key: 'meta_ads:campaign:c1:cpa',
    kind: 'issue',
    status: 'experimenting',
    title: 'Meta "Kurta Sale" costs more per sale',
    entity_level: 'campaign',
    entity_key: 'c1',
    entity_name: 'Kurta Sale',
    channel_id: 'meta_ads',
    window: { start: '2026-10-08', end: '2026-10-14' },
    first_seen: '2026-10-14',
    primary_metric: 'cpa',
    primary_detector: 'baseline_change',
    current: 610,
    baseline: 420,
    change_pct: 45.2,
    impact: -31000,
    confidence: 0.82,
    priority: 25420,
    band: 'high',
    age_days: 3,
    signal_count: 4,
    cause: 'creative_fatigue',
    cause_label: 'Creative fatigue',
    observation: 'CPA rose 45% over 7 days.',
    diagnosis_source: 'llm',
    dismissed_reason: null,
    ...overrides,
  }
}

export function experimentRow(overrides: Partial<Experiment> = {}): Experiment {
  return {
    id: 10,
    status: 'draft',
    action: 'rotate_creative',
    hypothesis: 'Rotating in a fresh creative should move CPA from ₹610 to ₹420 within 7 days.',
    metric: 'cpa',
    baseline: 610,
    target: 420,
    duration_days: 7,
    started_on: null,
    ends_on: null,
    progress: null,
    verdict: null,
    before: null,
    after: null,
    sample_days: null,
    evaluated_on: null,
    reason: null,
    opportunity: opportunityRow(),
    ...overrides,
  }
}

export function decisionRow(overrides: Partial<Decision> = {}): Decision {
  return {
    id: 100,
    kind: 'approve',
    reason: null,
    impact: -31000,
    at: '2026-10-14T09:30:00',
    opportunity: opportunityRow(),
    experiment: experimentRow({ status: 'running' }),
    ...overrides,
  }
}
