# Architecture

MDIA turns weekly CSV exports into decisions a marketing team can defend: trusted KPIs, then
signals judged against the business goals, then a diagnosis with its evidence, a recommendation, an
experiment, and a logged outcome. It is a pipeline, not a chatbot — you never ask it anything.

```
CSV exports ─► ingestion ─► facts (Postgres)
                              │
                              ├─► metrics ────────────► Today, charts
                              ├─► trust, pacing ──────► gating, banners
                              └─► signals ─► opportunities ─► investigation ─► recommendation
                                                                  │
                                                     experiment ─► verdict ─► decision log ─► weekly report
```

## The one rule: deterministic first

Anything that can be computed is code. The LLM never produces a number that reaches a user.

| Computed in `domain/` (pure functions) | Written by the LLM in `agents/` |
|---|---|
| KPIs, MER, break-even ROAS, goal status | ranking and phrasing hypotheses from given evidence |
| change detection, scoring, opportunity grouping | choosing an action **from the catalogue**, and its rationale |
| the decomposition / evidence tree | alternative explanations |
| trust checks, pacing, suppression | the weekly report narrative |
| confidence, priority, guardrails, experiment verdicts | |

Consequences of taking that seriously:

- **Ratios are recomputed, never averaged.** `domain/kpi.py` builds every ratio from summed base
  measures — the ratio of sums, not the mean of ratios. Property tests hold the line.
- **The evidence tree is arithmetic.** `domain/decomposition.py` splits a movement along
  `CPA = CPC / CVR`, `ROAS = CVR × AOV / CPC` and `CPC = CPM / (1000·CTR)` with log-change
  attribution, so the contributions sum to 100 %.
- **Confidence is a formula, not a feeling.** `domain/recommendations.py`:
  `0.35 ×` signal strength `+ 0.20 ×` agreement between signals `+ 0.20 ×` the share of the movement
  explained `+ 0.25 ×` data trust, floored at `0.10`. Priority is `₹ impact × confidence`.
- **`domain/` is 18 flat modules and ~2,900 lines with no imports of the database, HTTP, LangChain or
  the environment.** That is what makes the maths testable; coverage is gated at 80 % (it sits at
  ~97 %, NFR-9).

## Layers

```
api/routes  →  services/  →  repositories/  |  domain/  |  agents/
```

| Layer | Allowed to | Never |
|---|---|---|
| `api/routes/` | parse a request, call one service, return a schema | contain logic |
| `services/` | orchestrate repos + domain + agents, own the transaction | do arithmetic itself |
| `repositories/` | query and write | know business rules |
| `domain/` | pure functions over dataframes and dataclasses | touch DB, HTTP, LLM, env |
| `agents/` | prompt, validate, ground, fall back | touch the DB or compute a number |

Three sets of types stay separate on purpose: `models/` (ORM rows), `schemas/` (API DTOs, the source
of the frontend's generated types) and `agents/schemas.py` (what the LLM is allowed to return).
Failures share one shape — `api/errors.py` maps every domain error to an `ErrorOut`, so the client
has one thing to parse and the frontend has one `ApiError` to read.

Storage is deliberately thin: facts plus JSONB for a run's `signals`, `evidence`, `diagnosis` and
`recommendation`. No aggregate tables, no materialised KPIs — metrics, trust and pacing are computed
on request, which keeps "what the numbers mean" in one place instead of two.

## Trust gating

Trust is the gate in front of everything else, because advice built on a broken pixel is worse than
silence. `domain/trust.py` gives each source `ok | warning | broken` from two checks:

- **Missing days and sources** inside a 28-day freshness window — old gaps don't affect today.
- **A tracking break**: the last 3 days' platform-reported conversions per store order, against the
  channel's own 28-day baseline. Below `0.6` is a warning, below `0.45` is broken. On the 365-day
  evaluation data ordinary days — festive peaks and genuine performance problems included — stay
  above ~0.68, while a broken pixel falls to ~0.15 within three days.

What the status then does, all in code:

1. `domain/scoring.py` suppresses signals **before** scoring: nothing performance-related is raised
   for a broken channel, and nothing for a festive window. The one exception is the tracking break
   itself — that is the only thing worth saying about a channel whose numbers are missing.
2. ROAS and CPA are marked untrustworthy wherever they are shown (they are built on platform
   conversions; revenue, spend and MER are not), and the Today screen greys them out.
3. Trust feeds the confidence formula, so surviving recommendations are visibly less certain.
4. The recommendation becomes "fix the tracking first" — which is also a testable experiment.

Scoring keeps the rest honest: a signal needs `|Δ| × ₹ impact ≥ ₹5,000` to be worth a marketer's
attention, so a dramatic swing on a campaign spending nothing stays quiet.

## The two graphs, and the grounding guard

Both LangGraph graphs are small, checkpointer-free, and shaped so the LLM is an enhancement rather
than a dependency.

```
investigation:  build_evidence → diagnose (LLM) → ground_check ⟲ ≤2 → finalize
report:         prepare        → narrate  (LLM) → ground_check ⟲ ≤2 → finalize
```

- The node after `START` routes straight to `finalize` when no model is configured, so an outage is
  a branch, not an exception.
- The LLM node carries `RetryPolicy(max_attempts=3)` for transport failures, and the conditional
  edge back into it carries *content* failures — up to two retries with the violations fed back as
  feedback.
- `finalize` is where confidence, guardrails and priority are computed, in code, whatever the answer
  came from. A protected campaign can never be handed a `pause_*` action.
- Everything that leaves is labelled `llm` or `rules`, and the UI says which.

`agents/grounding.py` is the guard (FR-8.3): an answer may contain only what it was given. It
rejects

- **signal IDs** that are not in the evidence,
- **action types** outside the catalogue, or with parameters that don't validate,
- **numbers** that are not in the evidence — read as a person would read them, so `₹16.39 L` and
  `1639000` are the same number, within 2 % or 0.5 absolute.

Every call, its prompt version, and whether it was rejected is written to `llm_calls`, which is what
the grounding report in `evaluation/` scores: violations before the guard versus after.

`services/analysis.py` runs after each upload as a background task. The top five opportunities by
score get the LLM one after another; the rest are diagnosed by the rules. The pipeline finishes
either way — the analysis never blocks on the model.

## Evaluation stays outside

The generator writes a `ground_truth.json` next to every batch of CSVs. `evaluation/` is the only
package allowed to read it — detection precision/recall and days-to-detect, diagnosis top-1/top-3,
trust accuracy, grounding violation rate. `backend/tests/unit/test_no_ground_truth.py` fails if any
backend module so much as mentions it, because a system that can see the answers proves nothing.

## Frontend

React 19 + Vite + TypeScript, feature folders (`features/<name>/{api.ts,page.tsx,components/}`) that
never import each other's internals. Server state lives in TanStack Query only; `api.ts` holds the
fetchers and hooks, so components stay presentational. Types are generated from the OpenAPI schema
(`npm run gen:api`) — the API's shape is not retyped by hand.

Failures have one path each: queries show an error card with a retry, writes announce themselves
once through the mutation cache as a toast, rejected fields mark the inputs that caused them, and a
route-keyed error boundary catches a screen that crashes outright. Visual choices come only from the
tokens in `requirements/designSystem.md`; colour carries business meaning (a fall in a cost metric
is green), and anything the trust check distrusts is greyed out rather than coloured.

## Reading order

`requirements/requirements.md` for the FR/NFR IDs, `requirements/task.md` for the build order,
`docs/demo.md` for the demo runbook, and `CLAUDE.md` for the house rules that keep the layers apart.
