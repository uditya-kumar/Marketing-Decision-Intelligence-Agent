# MDIA — Task Breakdown

Progressive order: each phase builds on the previous one and ends in something demoable.
Tasks are small (≈ 0.5–1 day). Tick `[x]` when **Done when** passes. Refs → `requirements.md`, `UI.md`.

---

## Phase 0 — Foundation & Tooling

- [ ] **0.1** Git init, `.gitignore` (Python, Node, `.env`, `generator/output/`), `README.md`.
  Done when: first commit exists.
- [x] **0.2** Folder skeleton per requirements §10.
  Done when: tree matches §10.
- [x] **0.3** `backend/`: `uv init`; FastAPI, Uvicorn, Pydantic v2, pydantic-settings; Ruff + mypy config.
  Done when: `uv run ruff check` and `uv run mypy src` pass.
- [x] **0.4** `core/settings.py` + `.env.example` (DB URLs, LLM vars).
  Done when: missing env fails fast with a clear message.
- [x] **0.5** App factory + `GET /health`; structured logging.
  Done when: `/health` returns 200.
- [x] **0.6** Neon project + branches `main` / `dev` / `test`; URLs in `.env`.
  Done when: `/health` reports DB ok on `dev`.
- [x] **0.7** SQLAlchemy engine/session + Alembic init.
  Done when: empty migration applies on `dev`.
- [x] **0.8** pytest (unit / integration / agents markers; integration on `test` branch).
  Done when: sample test per folder passes.
- [ ] **0.9** `npm create vite@latest frontend` → React + TypeScript + React Compiler.
  Done when: `npm run dev` serves starter.
- [ ] **0.10** Tailwind v4 (`@tailwindcss/vite`), `@/` alias, `npx shadcn@latest init`.
  Done when: shadcn `Button` renders.
- [ ] **0.11** React Router, TanStack Query, Zod; `app/` with providers + layout shell (sidebar, top bar) per `UI.md §3`.
  Done when: all sidebar routes navigate to placeholder pages.
- [ ] **0.12** pre-commit (Ruff, mypy, ESLint, Prettier).
  Done when: `pre-commit run --all-files` passes.

---

## Phase 1 — Synthetic Data Generator — FR-2

- [ ] **1.1** `generator/` uv package; `world.yaml` (NovaWear channels, campaigns, ad sets, creatives, segments).
  Done when: config loads into typed models.
- [ ] **1.2** Seeded demand model with weekly seasonality + noise.
  Done when: same seed ⇒ identical output (test).
- [ ] **1.3** Spend → impressions → clicks → conversions → revenue chain per ad set.
  Done when: KPIs in realistic ranges (test).
- [ ] **1.4** Diminishing returns (Hill) per channel.
  Done when: 2× spend < 2× conversions (test).
- [ ] **1.5** Frequency-driven creative fatigue.
  Done when: CTR decay visible in a plot script.
- [ ] **1.6** Festive calendar multipliers (Diwali, EOSS).
  Done when: spikes on configured dates.
- [ ] **1.7** Web funnel + store orders linked to ad traffic; platform conversions ≠ store orders by a realistic attribution ratio.
  Done when: store orders reconcile within tolerance.
- [ ] **1.8** Scenario framework + `ground_truth.json` recorder.
  Done when: a no-op scenario writes an entry.
- [ ] **1.9** Scenarios: `creative_fatigue`, `audience_mismatch`, `landing_page_break`.
  Done when: each produces the expected pattern (test).
- [ ] **1.10** Scenarios: `cpc_spike`, `channel_opportunity`, `tracking_break`, `budget_overpace`.
  Done when: same.
- [ ] **1.11** Exporters in platform shapes: `google_ads.csv`, `meta_ads.csv`, `web_analytics.csv`, `store_orders.csv`.
  Done when: column names resemble real exports.
- [ ] **1.12** CLI: `novawear-sim backfill --days 180 --seed 42` and `batch --from <date> --days 7`.
  Done when: both commands write CSVs + ground truth.
- [ ] **1.13** `scenarios.yaml` evaluation schedule (~50 events + no-issue windows) and a short **demo** schedule.
  Done when: both schedules generate.

---

## Phase 2 — Data Model & Ingestion — FR-3

- [ ] **2.1** ORM + migration: dims, `fact_ad_daily`, `fact_web_daily`, `fact_store_daily`, `ingestion_runs`.
  Done when: `alembic upgrade head` on `dev`.
- [ ] **2.2** Repositories with idempotent bulk upsert.
  Done when: same file twice ⇒ same row counts (integration test).
- [ ] **2.3** Source templates (`ingestion/templates/`) + auto-detect source from headers.
  Done when: each generator CSV is recognised.
- [ ] **2.4** `Connector` base + `CsvConnector` with row validation and rejected-row report.
  Done when: malformed rows reported, valid rows loaded.
- [ ] **2.5** `IngestionService` + `POST /ingestion/upload`, `GET /ingestion/runs`, `GET /ingestion/templates`; as-of date computed.
  Done when: 180-day backfill loads via API.
- [ ] **2.6** Guard test: no backend code path references `ground_truth`.
  Done when: test passes.

---

## Phase 3 — Business Profile & Goals — FR-1

- [ ] **3.1** Tables + migration: `business_profile`, `goals`, `budget_plans`, `calendar_events`, `guardrails`.
  Done when: migration applied.
- [ ] **3.2** `domain/goals/`: break-even ROAS, contribution margin, goal status (`ahead | on_track | behind`).
  Done when: unit tests pass.
- [ ] **3.3** `/settings/*` endpoints with validation.
  Done when: CRUD works via OpenAPI docs.
- [ ] **3.4** Generate TS types from OpenAPI → `types/api.ts`; `lib/api-client.ts`, `lib/format.ts` (₹ lakh/crore, %, deltas).
  Done when: frontend compiles against generated types.
- [ ] **3.5** Settings page (Profile, Goals, Budgets, Calendar, Guardrails sections) per `UI.md`.
  Done when: values persist and reload.

---

## Phase 4 — KPI Layer & Today v1 — FR-4

- [ ] **4.1** `domain/kpi/registry.py` (base + blended/profit metrics).
  Done when: Hypothesis property tests pass (no div-by-zero, correct ratio aggregation).
- [ ] **4.2** Decomposition + log-change attribution.
  Done when: shares sum to 100 % (test).
- [ ] **4.3** `agg_metrics_daily` + refresh after ingestion.
  Done when: aggregates equal on-the-fly computation (test).
- [ ] **4.4** `MetricsService.query(metric, dims, grain, range, compare_to, vs_goal)`.
  Done when: returns deltas and goal gaps.
- [ ] **4.5** `GET /metrics`, `GET /today` (KPI summary only).
  Done when: typed responses in OpenAPI.
- [ ] **4.6** Today v1: greeting + as-of date, KPI strip (Revenue, Spend, ROAS, MER, CPA) with deltas and goal markers, trend chart.
  Done when: **Demo 1** — real numbers render.

---

## Phase 5 — Data Trust — FR-5

- [ ] **5.1** `domain/trust/freshness.py`: missing days/sources, partial days.
  Done when: unit tests with gaps pass.
- [ ] **5.2** `domain/trust/tracking.py`: platform-vs-store divergence against historical ratio.
  Done when: `tracking_break` scenario flagged; normal attribution noise not flagged.
- [ ] **5.3** Attribution gap trend.
  Done when: computed per channel/day.
- [ ] **5.4** `trust_checks` table, `TrustService`, `GET /trust`; runs after ingestion.
  Done when: statuses stored per source/day.
- [ ] **5.5** Trust banner on Today + trust badges on Data page.
  Done when: **Demo 2** — "Meta tracking looks broken; don't change campaigns yet."

---

## Phase 6 — Signal Engine — FR-6

- [ ] **6.1** Detector interface.
  Done when: interface + trivial detector tested.
- [ ] **6.2** Rolling-baseline detector with min-sample guard.
  Done when: detects step change, ignores low volume.
- [ ] **6.3** STL robust z-score detector; festive windows suppressed via calendar.
  Done when: weekly/festive patterns not flagged; injected anomaly flagged.
- [ ] **6.4** Change-point detector (ruptures).
  Done when: fatigue onset within ±2 days.
- [ ] **6.5** Funnel-divergence + cross-segment detectors.
  Done when: `landing_page_break` and `audience_mismatch` produce correct types.
- [ ] **6.6** Goal-breach detector.
  Done when: CPA above target ⇒ goal signal.
- [ ] **6.7** Scoring + threshold + dedup.
  Done when: ordering matches expectation on fixtures.
- [ ] **6.8** `signals` table, `SignalService.run(range)`; skips sources marked `broken`.
  Done when: signals stored after upload.
- [ ] **6.9** Evaluation v0 (`evaluation/detection.py`).
  Done when: first precision/recall report; thresholds tuned toward §13.

---

## Phase 7 — Budget Pacing — FR-7

- [ ] **7.1** `domain/pacing/`: MTD vs plan, run-rate projection, status, suggested daily spend.
  Done when: unit tests pass incl. month boundaries.
- [ ] **7.2** `pacing_snapshots`, `GET /pacing`; pacing signals emitted.
  Done when: `budget_overpace` scenario flagged.
- [ ] **7.3** Pacing card on Today.
  Done when: **Demo 3** — "62 % spent, 45 % of month gone."

---

## Phase 8 — LLM Layer & LangGraph Basics

- [ ] **8.1** Add `langgraph`, `langchain`, `langchain-aws`, `langchain-google-genai`.
  Done when: imports resolve.
- [ ] **8.2** `agents/llm/factory.py::get_chat_model(role)` via `init_chat_model`.
  Done when: Bedrock smoke test responds.
- [ ] **8.3** Structured-output helper + `llm_calls` logging.
  Done when: toy schema returns validated object + log row.
- [ ] **8.4** Fake chat model for tests.
  Done when: agent tests run offline.
- [ ] **8.5** Versioned prompt registry.
  Done when: prompt version logged.
- [ ] **8.6** Postgres checkpointer on Neon.
  Done when: test graph resumes by `thread_id`.

---

## Phase 9 — Investigation Graph — FR-8

- [ ] **9.1** `domain/signals/clustering.py` → opportunities.
  Done when: one scenario ⇒ one opportunity.
- [ ] **9.2** `opportunities`, `hypotheses` tables.
  Done when: migration applied.
- [ ] **9.3** `InvestigationState` with reducers.
  Done when: typed.
- [ ] **9.4** Nodes `load_context`, `decompose` (evidence tree).
  Done when: fatigue case attributes CPA change to CTR/CVR.
- [ ] **9.5** `domain/diagnosis/rules.py` rule-based diagnosis.
  Done when: ≥ 3 scenario types labelled correctly.
- [ ] **9.6** Node `hypothesise` (LLM, structured, `RetryPolicy`).
  Done when: returns observation, hypotheses with evidence IDs, alternatives.
- [ ] **9.7** `agents/guards/grounding.py`.
  Done when: fabricated IDs/numbers caught (unit tests).
- [ ] **9.8** `ground_check` + retry ≤ 2 → rule fallback.
  Done when: "lying" fake LLM ends in fallback path.
- [ ] **9.9** Compile + persist.
  Done when: end-to-end with Bedrock on a real opportunity.
- [ ] **9.10** `GET /opportunities[/{id}]`, dismiss.
  Done when: detail returns observation / evidence / hypotheses separately.
- [ ] **9.11** Opportunity page: Observation, Evidence, Hypothesis sections + charts per `UI.md`.
  Done when: renders for each scenario type.
- [ ] **9.12** Evidence tree (React Flow).
  Done when: **Demo 4** — click an opportunity, see *why*.

---

## Phase 10 — Recommendations — FR-9

- [ ] **10.1** Action catalogue + param validation.
  Done when: invalid params rejected.
- [ ] **10.2** Computed confidence model (incl. data-trust term).
  Done when: monotonic property tests pass.
- [ ] **10.3** Guardrail enforcement in code.
  Done when: protected campaign never gets `pause_*`.
- [ ] **10.4** `recommendations` table; nodes `score_confidence`, `recommend`, `apply_guardrails`.
  Done when: recommendation has impact range, risk, KPI, stop condition.
- [ ] **10.5** Priority ranking.
  Done when: ordering follows ₹ impact × confidence.
- [ ] **10.6** Recommendation card UI + actions (Simulate / Create experiment / Dismiss).
  Done when: buttons wired (later features disabled until built).

---

## Phase 11 — Briefing Pipeline & Today v2

- [ ] **11.1** `briefing` graph with `Send` fan-out.
  Done when: N opportunities investigated in parallel.
- [ ] **11.2** `pipeline/`: ingest → aggregates → trust → signals → pacing → briefing (background task).
  Done when: upload triggers full pipeline; status visible.
- [ ] **11.3** Pipeline status endpoint + UI progress ("Analysing 7 new days…").
  Done when: UI updates when done.
- [ ] **11.4** Today v2 per `UI.md`: trust banner, Needs attention, Opportunities, Pacing, Active experiments.
  Done when: **Demo 5** — "3 things need your attention."

---

## Phase 12 — Simulator & Planner — FR-10

- [ ] **12.1** Response-curve fitting + bootstrap bands.
  Done when: recovers generator parameters within tolerance.
- [ ] **12.2** What-if projection.
  Done when: held-out error within target.
- [ ] **12.3** Planner optimiser with guardrails.
  Done when: never all-in on one channel under saturation.
- [ ] **12.4** `simulations` table, `POST /simulations`, `POST /simulations/plan`.
  Done when: API returns projections.
- [ ] **12.5** `simulate` node for budget actions.
  Done when: budget recommendations carry a simulation.
- [ ] **12.6** Plan page: sliders, current vs proposed, "Suggest best split".
  Done when: **Demo 6** — move ₹10K Instagram → Google, see impact.

---

## Phase 13 — Experiments (lite) — FR-11

- [ ] **13.1** `experiments`, `experiment_results`, `decisions` tables.
  Done when: migration applied.
- [ ] **13.2** `experiment` graph: `draft → interrupt(approval)`.
  Done when: pause survives server restart.
- [ ] **13.3** `POST /experiments/{id}/decision` resumes (approve / edit / reject).
  Done when: each branch tested.
- [ ] **13.4** `domain/experiments/evaluation.py`: before/after + min-sample → verdict.
  Done when: unit tests for worked / did_not_work / inconclusive.
- [ ] **13.5** Pipeline evaluates due experiments after each upload.
  Done when: uploading the next batch completes the experiment.
- [ ] **13.6** Experiments page: Awaiting approval, Running (day X/Y), Completed (verdict).
  Done when: **Demo 7** — approve → upload next week → "Worked."

---

## Phase 14 — Decision Memory (lite) — FR-12

- [ ] **14.1** Chain query service.
  Done when: one call returns signal → outcome chain.
- [ ] **14.2** Similar-case lookup; `retrieve_memory` node wired.
  Done when: repeated fatigue finds prior case.
- [ ] **14.3** Decisions page (timeline + search) and "Similar past decisions" on Opportunity.
  Done when: **Demo 8** — "Why did we pause that?" answered.

---

## Phase 15 — Weekly Reports — FR-13

- [ ] **15.1** `domain/reports/`: assemble weekly payload (KPIs vs goals, WoW, pacing, opportunities, decisions, experiments).
  Done when: payload unit-tested against fixtures.
- [ ] **15.2** `report` graph: narrate (Founder + Team) → ground_check ⟲.
  Done when: every number in text matches payload.
- [ ] **15.3** `reports` table, `POST /reports/weekly`, `GET /reports[/{id}]`.
  Done when: history persisted.
- [ ] **15.4** Reports page: Founder/Team toggle, copy, export Markdown, print-to-PDF styles.
  Done when: **Demo 9** — Friday report in one click.

---

## Phase 16 — Analyst — FR-14

- [ ] **16.1** Read-only tools.
  Done when: each tool unit-tested.
- [ ] **16.2** `analyst` ReAct graph + threads.
  Done when: multi-turn resumes.
- [ ] **16.3** `POST /analyst/stream` (SSE).
  Done when: curl shows streamed tokens + tool events.
- [ ] **16.4** Analyst side panel (⌘J) with tool-step chips and clickable citations; context-aware of current page.
  Done when: opens from any page.

---

## Phase 17 — Onboarding & UX Polish — `UI.md`, `designSystem.md`

- [ ] **17.1** Apply `designSystem.md` tokens (colour, type, spacing, radius, motion) to Tailwind theme + shadcn.
  Done when: all screens use tokens only (no ad-hoc values).
- [ ] **17.2** Onboarding flow (3 steps: Business → Goals & budget → Upload data).
  Done when: new user reaches Today in < 5 min (NFR-10).
- [ ] **17.3** Data page: drag-drop upload, detected source, validation results, run history.
  Done when: bad CSV shows row-level errors.
- [ ] **17.4** Command palette (⌘K): navigate, search opportunities/decisions, quick actions.
  Done when: every page reachable by keyboard.
- [ ] **17.5** Empty, loading (skeleton), and error states for every screen.
  Done when: checklist in `UI.md §7` passes.
- [ ] **17.6** Light/dark theme, responsive down to tablet.
  Done when: visual check passes on both.

---

## Phase 18 — Hardening

- [ ] **18.1** API error schema, toasts, error boundaries; LLM outage ⇒ rule fallback shown.
- [ ] **18.2** Indexes / query tuning; meet NFR-6.
- [ ] **18.3** LLM cache by input hash for eval runs.
- [ ] **18.4** `domain/` coverage ≥ 80 %; Vitest for key components.

---

## Phase 19 — Provider Switch: Bedrock → Gemini — NFR-4

- [ ] **19.1** Gemini env + smoke test.
- [ ] **19.2** Full agent suite on Gemini; fix only prompts/config.
- [ ] **19.3** Gemini as default; demo end-to-end.

---

## Phase 20 — Evaluation — FR-16

- [ ] **20.1** Detection report.
- [ ] **20.2** Diagnosis report (LLM vs rules).
- [ ] **20.3** Trust report (tracking-break accuracy, suppression correctness) + false positives.
- [ ] **20.4** Grounding report (pre/post guard).
- [ ] **20.5** Provider comparison.
- [ ] **20.6** User study (5 tasks × 3 workflows).
- [ ] **20.7** `report.py` → thesis tables/plots.
  Done when: all §13 criteria reported with numbers.

---

## Phase 21 — Presentation

- [ ] **21.1** Seeded demo schedule + upload order for the "Monday morning" story.
- [ ] **21.2** `docs/architecture.md` + ADRs (LangGraph, deterministic-first, grounding guard, trust gating).
- [ ] **21.3** README: setup, run, demo.
- [ ] **21.4** Slides: problem → users → architecture → live demo → evaluation → "why not ChatGPT" with data.
- [ ] **21.5** Dress rehearsal from a clean clone.

---

## Stretch (only if time allows) — requirements §8

- [ ] **S-1** Difference-in-differences with control campaign.
- [ ] **S-2** Action-aware generator (`batch --actions actions.json`).
- [ ] **S-3** Historical success rate in confidence model.
