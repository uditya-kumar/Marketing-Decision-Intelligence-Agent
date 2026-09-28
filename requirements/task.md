# MDIA — Task Breakdown

This is a capstone-sized plan. Each phase builds on the previous one and ends with something you can demo.
Tasks are small (about 0.5–1 day each). Tick `[x]` when **Done when** passes. Refs → `requirements.md`, `UI.md`.

**Frontend tasks:** open `requirements/designFile.pen` with the pencil MCP first, and use only the tokens in `designSystem.md`.
Every screen gets its empty, loading and error states when it is built, not in a later polish pass.

---

## Phase 0 — Foundation & Tooling ✅

- [x] **0.1** Git init, `.gitignore`, `README.md`.
- [x] **0.2** Folder skeleton.
- [x] **0.3** `backend/` with uv, FastAPI, Pydantic v2, Ruff + mypy.
- [x] **0.4** `core/settings.py` + `.env.example`; missing env fails fast.
- [x] **0.5** App factory + `GET /health`; structured logging.
- [x] **0.6** Neon project + branches `main` / `dev` / `test`.
- [x] **0.7** SQLAlchemy engine/session + Alembic.
- [x] **0.8** pytest (`integration` marker runs on the `test` branch).
- [x] **0.9** Vite + React + TypeScript + React Compiler.
- [x] **0.10** Tailwind v4, `@/` alias, shadcn.
- [x] **0.11** React Router, TanStack Query; layout shell.
- [x] **0.12** pre-commit (Ruff, mypy, ESLint, Prettier).

---

## Phase 1 — Synthetic Data Generator (FR-2) ✅

- [x] **1.1–1.7** NovaWear world, seeded demand, the spend → revenue chain, saturation, fatigue, festive calendar, and web + store data that reconcile.
- [x] **1.8–1.10** Scenario framework, `ground_truth.json`, and all seven scenarios.
- [x] **1.11–1.13** Platform-shaped exporters, the `backfill` / `batch` CLI, and evaluation + demo schedules.

---

## Phase 2 — Data Model & Ingestion (FR-3) ✅

- [x] **2.1** ORM + migration: dims, `fact_ad_daily`, `fact_web_daily`, `fact_store_daily`, `ingestion_runs`.
  Done when: `alembic upgrade head` succeeds on `dev`.
- [x] **2.2** Idempotent bulk upsert in the repositories.
  Done when: loading the same file twice gives the same row counts (integration test).
- [x] **2.3** Source templates (`ingestion/templates.py`) + detecting the source from headers.
  Done when: each generator CSV is recognised.
- [x] **2.4** CSV reader with row validation and a rejected-row report.
  Done when: malformed rows are reported and valid rows are loaded.
- [x] **2.5** `IngestionService` + `POST /ingestion/upload`, `GET /ingestion/runs`, `GET /ingestion/status`, `GET /ingestion/templates`; as-of date computed.
  Done when: the 180-day backfill loads via the API (integration test).
- [x] **2.6** Guard test: no backend code references `ground_truth`.
  Done when: the test passes.

---

## Phase 3 — Settings, KPIs & Today v1 (FR-1, FR-4)

- [x] **3.1** `settings` table (a single row: margin, targets, monthly budget per channel, festive windows, protected campaigns) + `GET/PUT /settings`.
  Done when: values persist; invalid values (margin ≤ 0, negative budget) give a 422.
- [x] **3.2** `domain/goals.py`: break-even ROAS and goal status (`ahead | on_track | behind`).
  Done when: unit tests pass.
- [x] **3.3** `domain/kpi.py`: ratio KPIs from base measures (CTR, CPC, CPM, CVR, CPA, ROAS, AOV, frequency, MER).
  Done when: Hypothesis property tests pass (no division by zero; the ratio of sums, not the mean of ratios).
- [x] **3.4** `domain/decomposition.py`: `CPA = CPC / CVR`, `ROAS = CVR × AOV / CPC`, `CPC = CPM / (1000·CTR)`, with log-change attribution.
  Done when: the contribution shares sum to 100 % (test).
- [x] **3.5** `MetricsService` (on-the-fly SQL + pandas; no aggregate table) + `GET /metrics` (KPI by channel/campaign per day, compared with the previous period) + `GET /today` (KPI summary).
  Done when: values match a hand calculation on the fixtures.
- [x] **3.6** Frontend base: apply the `designSystem.md` tokens; `npm run gen:api` → `types/api.ts`; `lib/api-client.ts`; `lib/format.ts` (₹ lakh/crore, %, deltas); common `KpiCard`, `Delta`, `EmptyState`.
  Done when: the frontend compiles against the generated types.
- [x] **3.7** Data page: drag-drop upload, the detected source per file, row errors, source status, run history.
  Done when: uploading a bad CSV shows row-level errors.
- [x] **3.8** Settings page (one form).
  Done when: values persist and reload.
- [x] **3.9** Today v1: as-of date, the KPI strip (Revenue, Spend, ROAS, MER, CPA) with deltas and goal markers, a 30-day trend chart; empty state linking to Settings and Data.
  Done when: **Demo 1** — real numbers render after uploading the backfill.

---

## Phase 4 — Data Trust & Pacing (FR-5, FR-7)

- [x] **4.1** `domain/trust.py`: missing days and sources, and tracking break (platform conversions vs store orders against the channel's historical ratio). Status per source: `ok | warning | broken`.
  Done when: the `tracking_break` scenario is flagged and normal attribution noise is not.
- [x] **4.2** `domain/pacing.py`: month-to-date spend vs budget, run-rate projection, status, suggested daily spend.
  Done when: unit tests pass, including month boundaries.
- [x] **4.3** `TrustService` / `PacingService` (computed on request; not stored) + `GET /trust`; both included in `GET /today`.
  Done when: the `budget_overpace` scenario shows `over`.
- [x] **4.4** UI: trust banner on Today, trust badges on the Data page, pacing card on Today.
  Done when: **Demo 2** — "Meta tracking looks broken; don't change campaigns yet."

---

## Phase 5 — Signals & Opportunities (FR-6)

- [ ] **5.1** `domain/signals.py` detectors: rolling-baseline change (with a minimum-sample guard), goal breach, funnel-step drop, and segment divergence (age group within an ad set).
  Done when: each detector has a positive and a negative unit test.
- [ ] **5.2** Scoring (`|Δ| × ₹ impact`), a threshold, and suppression in festive windows and for `broken` sources.
  Done when: festive spikes and tracking-broken channels produce no performance signals.
- [ ] **5.3** `domain/opportunities.py`: group signals by entity + window into opportunities, with a stable key for dedup.
  Done when: one injected scenario gives one opportunity.
- [ ] **5.4** `analysis_runs` + `opportunities` tables (signals, evidence, diagnosis and recommendation as JSONB); `AnalysisService.run()` runs as a background task after each upload; `GET /analysis/status`.
  Done when: uploading the backfill stores opportunities and the status goes `running → done`.
- [ ] **5.5** Evaluation v0 (`evaluation/`): upload the evaluation schedule, then compute detection precision/recall against `ground_truth.json`.
  Done when: the first report prints; thresholds are tuned toward §13.

---

## Phase 6 — LLM Investigation (FR-8, FR-9)

- [ ] **6.1** `agents/llm.py`: `get_chat_model()` via `init_chat_model` (Bedrock now; Gemini by env), a structured-output call at temperature 0, and `llm_calls` logging.
  Done when: a Bedrock smoke test returns a validated object and a log row.
- [ ] **6.2** Fake chat model for tests (`tests/fakes.py`).
  Done when: agent tests run offline.
- [ ] **6.3** `domain/diagnosis.py`: evidence tree from the decomposition + rule-based diagnosis.
  Done when: at least 5 of the 7 scenario types get the right label.
- [ ] **6.4** `domain/recommendations.py`: action catalogue + param validation, computed confidence (including a data-trust term), a guardrail for protected campaigns, and priority = ₹ impact × confidence.
  Done when: confidence is monotonic (property test) and a protected campaign never gets `pause_*`.
- [ ] **6.5** `agents/grounding.py`: every signal ID, action type and number in LLM output must exist in the evidence.
  Done when: fabricated IDs and numbers are caught (unit tests).
- [ ] **6.6** `agents/investigation.py` graph: `build_evidence → diagnose (LLM) → ground_check → retry ≤ 2 | rules fallback → finalize (confidence, guardrails, priority in code)`, with a `RetryPolicy` on the LLM node.
  Done when: a "lying" fake LLM ends in the fallback; with Bedrock, a real opportunity is diagnosed.
- [ ] **6.7** Wire the graph into `AnalysisService`, investigating the top N opportunities one after another; the pipeline still finishes if the LLM is down.
  Done when: uploading the backfill gives diagnosed opportunities, each labelled `llm` or `rules`.

---

## Phase 7 — Opportunity UI & Today v2

- [ ] **7.1** `GET /opportunities` (filter by status), `GET /opportunities/{id}`, `POST /opportunities/{id}/dismiss` (with a reason).
  Done when: the detail returns what happened, evidence, likely cause and recommendation as separate sections.
- [ ] **7.2** Opportunities list page (All · Issues · Wins · Dismissed).
  Done when: the filters work.
- [ ] **7.3** Opportunity detail page in the `UI.md §5.2` order, with the evidence tree as an indented list, an `AiBlock` with a "grounded ✓" marker, and charts.
  Done when: it renders for every scenario type.
- [ ] **7.4** Today v2: trust → KPIs → Needs attention → Opportunities + Pacing → Experiments; an "All clear" state; an "Analysing…" state while a run is in progress.
  Done when: **Demo 3** — "3 things need your attention", and clicking one shows *why*.

---

## Phase 8 — Experiments & Decision Log (FR-11, FR-12)

- [ ] **8.1** `experiments` + `decisions` tables; `POST /experiments` (auto-filled from an opportunity), `POST /experiments/{id}/approve|reject`, `GET /experiments`, `GET /decisions`.
  Done when: approve, reject and dismiss each write a decision row.
- [ ] **8.2** `domain/experiments.py`: before vs after on the primary metric, with a minimum sample → `worked | did_not_work | inconclusive`.
  Done when: unit tests cover all three verdicts.
- [ ] **8.3** `AnalysisService` evaluates due experiments after each upload.
  Done when: uploading the next `batch` completes a running experiment.
- [ ] **8.4** Experiments page (Awaiting approval · Running with day X/Y · Completed with verdict) + "Create experiment" on the opportunity page.
  Done when: the approve → running flow works in the UI.
- [ ] **8.5** Decisions page: a timeline of decisions, each linking to its opportunity → experiment → outcome.
  Done when: **Demo 4** — approve → upload next week → "Worked ✓", visible in Decisions.

---

## Phase 9 — Weekly Report (FR-13)

- [ ] **9.1** `domain/reports.py`: weekly payload (KPIs vs goals, week-on-week, pacing, top opportunities, decisions, experiment results).
  Done when: the payload is unit-tested against fixtures.
- [ ] **9.2** `agents/report.py` graph: `narrate (LLM) → ground_check ⟲ → template fallback`.
  Done when: every number in the text matches the payload.
- [ ] **9.3** `reports` table, `POST /reports/weekly`, `GET /reports[/{id}]`.
  Done when: past reports are listed.
- [ ] **9.4** Reports page: week picker, a founder summary at the top and team detail below, copy as Markdown, print styles.
  Done when: **Demo 5** — the Friday report in one click.

---

## Phase 10 — Evaluation (FR-16)

- [ ] **10.1** Detection report: precision, recall, F1 and days-to-detect per scenario; false positives in no-issue windows.
- [ ] **10.2** Diagnosis report: top-1 / top-3 accuracy, LLM vs rules.
- [ ] **10.3** Trust report: tracking-break accuracy and whether suppression was correct.
- [ ] **10.4** Grounding report: violation rate before and after the guard (from `llm_calls`).
- [ ] **10.5** *(optional)* Baseline: the same CSVs given to a plain LLM prompt, scored the same way.
- [ ] **10.6** `report.py` → tables and plots for the thesis.
  Done when: every §13 criterion is reported with numbers.

---

## Phase 11 — Hardening & Presentation

- [ ] **11.1** One API error schema, toasts and error boundaries; an LLM outage shows the labelled rules result.
- [ ] **11.2** `domain/` coverage ≥ 80 %; Vitest for `format.ts` and the key components.
- [ ] **11.3** Demo script: seeded demo schedule + upload order for the "Monday morning" story.
- [ ] **11.4** `docs/architecture.md` (deterministic-first, grounding guard, trust gating) + README setup/run/demo.
- [ ] **11.5** Slides + a dress rehearsal from a clean clone.

---

## Stretch (only if time allows)

- [ ] **S-1** Budget simulator: per-channel response curves + a what-if slider page.
- [ ] **S-2** Analyst chat side panel (a ReAct agent with read-only tools).
- [ ] **S-3** Bedrock vs Gemini comparison run through the evaluation suite.
- [ ] **S-4** Difference-in-differences with a control campaign for experiment verdicts.
- [ ] **S-5** Action-aware generator (`batch --actions actions.json`).
- [ ] **S-6** Small user study (dashboard vs ChatGPT+CSV vs MDIA).
