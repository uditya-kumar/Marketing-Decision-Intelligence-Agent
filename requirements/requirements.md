# MDIA — Marketing Decision Intelligence Agent

> Dashboards tell marketers what happened. Chatbots answer what marketers ask.
> MDIA knows your goals, detects what matters, checks the data can be trusted, investigates why, recommends what to do, and checks whether it worked.

Companion docs: `task.md` (build plan) · `UI.md` (user flows & layout) · `designSystem.md` (visual system, provided later) · `CLAUDE.md` (agent guide)

---

## 1. Problem Statement

Marketing data is fragmented across ad platforms, web analytics, and the store. Every day a marketer manually compares numbers across tabs to find **what changed, whether the data is even correct, why it changed, and what to do**. Founders get screenshots but not answers. Decisions and their outcomes are lost in chat threads.

General-purpose LLMs analyse data only when someone supplies it and asks the right question. They do not know the company's goals, do not check data integrity, do not remember past decisions, and do not verify outcomes.

MDIA is a decision-support system where:

`CSV exports → Trusted KPIs → Goal-aware signals → Evidence-backed hypotheses → Recommendations → Experiments → Outcomes → Decision memory`

**Deterministic first:** metrics, detection, decomposition, trust checks, pacing, confidence, simulation, and experiment evaluation are code. The LLM only reasons over verified evidence and writes narrative.

---

## 2. Users

| Persona | Needs | Primary screens |
|---|---|---|
| **Founder** | "Are we making money? Spend more or less?" | Today (summary), Reports |
| **Performance marketer** | "What to kill, scale, or fix today and why?" | Today, Opportunity, Plan, Experiments |
| **Creative / content** | "What's working, what's fatiguing?" | Opportunity (creative signals) |

Single-company, single-role app for the capstone (role-based views are future work).

---

## 3. Scope

### In scope
- Synthetic D2C brand **NovaWear** (Indian fashion e-commerce); channels: Google Ads, Meta Ads, Instagram, Email, Website/Store
- **CSV upload** in platform-export shape as the only ingestion path (connector interface ready for real APIs)
- Business profile & goals, data trust checks, budget pacing, profit-aware KPIs
- Autonomous analysis on every upload, recommendations, lite experiments, decision memory
- Weekly reports (founder + team versions)
- Secondary tool-using analyst chat
- Quantitative evaluation against ground truth and a ChatGPT/Gemini baseline

### Out of scope (see §8 Future)
Real platform APIs, notifications (WhatsApp/Slack/email), multi-tenant auth, auto-executing changes on ad platforms.

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Backend runtime | Python 3.12, **uv** |
| API | FastAPI, Pydantic v2, Uvicorn |
| Database | **Neon (serverless Postgres)** — branches `main` / `dev` / `test` |
| ORM / migrations | SQLAlchemy 2.x (psycopg 3), Alembic |
| Analytics | pandas, NumPy, SciPy, statsmodels (STL), ruptures |
| Agent orchestration | **LangGraph** (StateGraph, Send, Command, interrupt, RetryPolicy) |
| Agent persistence | `langgraph-checkpoint-postgres` on Neon |
| LLM abstraction | LangChain `init_chat_model` + `with_structured_output(Pydantic)` |
| LLM providers | Phase 1 **Amazon Bedrock** (`langchain-aws`, `bedrock_converse`) → Phase 2 **Gemini** (`langchain-google-genai`, `google_genai`) — env switch only |
| Background work | FastAPI background tasks (pipeline triggered on ingestion) |
| Testing | pytest, pytest-asyncio, httpx, Hypothesis |
| Quality | Ruff, mypy, pre-commit |
| Frontend | **React 19 + React Compiler + Vite + TypeScript** |
| UI | Tailwind CSS v4, shadcn/ui, Recharts (shadcn charts), React Flow (`@xyflow/react`), lucide-react |
| Frontend data | TanStack Query, React Router, Zod, OpenAPI-generated types |
| Tooling | ESLint, Prettier, Vitest |

### LLM provider switching

```env
LLM_PROVIDER=bedrock_converse        # later: google_genai
LLM_MODEL=<bedrock-model-id>         # later: gemini-2.5-flash
LLM_TEMPERATURE=0
AWS_REGION=us-east-1
GOOGLE_API_KEY=
```

`agents/llm/factory.py::get_chat_model(role)` is the only place that knows about providers.

---

## 5. Architecture

```
┌────────────────────┐
│ generator/ (CLI)   │  writes platform-shaped CSVs + ground_truth.json
│ "fake Meta/Google/ │───────────────┐
│  GA4/Shopify"      │               │ user uploads CSV
└────────────────────┘               ▼
                        ┌─────────────────────────────┐
                        │ Ingestion (Connector API)   │
                        └──────────────┬──────────────┘
                                       ▼  triggers pipeline
  ┌──────────────┐      ┌─────────────────────────────┐
  │ Business     │─────▶│ KPI / Semantic Layer        │
  │ Profile/Goals│      └──────────────┬──────────────┘
  └──────┬───────┘                     ▼
         │              ┌─────────────────────────────┐
         │              │ Data Trust Checks           │── gates ──┐
         │              └──────────────┬──────────────┘           │
         │                             ▼                          │
         ├─────────────▶┌─────────────────────────────┐           │
         │              │ Signal Engine + Pacing      │           │
         │              └──────────────┬──────────────┘           │
         │                             ▼                          ▼
         │     ┌──────────────────── LangGraph ──────────────────────────┐
         │     │ briefing:      cluster → Send(investigation) × N → rank │
         └────▶│ investigation: decompose → memory → hypothesise(LLM)    │
               │                → ground-check ⟲ → confidence → recommend│
               │ experiment:    draft → interrupt(approval) → track      │
               │ report:        assemble(code) → narrate(LLM) → ground   │
               │ analyst:       ReAct, read-only tools                   │
               └───────────────────────┬─────────────────────────────────┘
                                       ▼
          Simulator/Planner · Experiments · Decision Memory · Reports
```

**Rule:** the backend never reads ground truth. Only `evaluation/` joins system output with `ground_truth.json`.

---

## 6. Functional Requirements

### FR-1 Business Profile & Goals
- FR-1.1 Profile: company name, currency (₹), timezone, fiscal month start.
- FR-1.2 Goals: target CPA, target ROAS, target MER, monthly revenue target.
- FR-1.3 Economics: gross margin % → derived **break-even ROAS** (`1 / margin`) and contribution margin.
- FR-1.4 Monthly budget per channel (used by pacing and planner).
- FR-1.5 Calendar: festive/sale periods (Diwali, EOSS) marked as expected-change windows.
- FR-1.6 Guardrails: protected campaigns (never recommend pausing), min/max spend per channel.
- FR-1.7 Signals and recommendations are evaluated **against goals**, not only against past values.

### FR-2 Synthetic Data Generator (external CLI tool)
- FR-2.1 Seeded, deterministic; outputs CSVs in realistic export shapes: `google_ads.csv`, `meta_ads.csv`, `web_analytics.csv` (GA4-like), `store_orders.csv` (Shopify-like daily).
- FR-2.2 Realistic dynamics: weekly seasonality, festive spikes, diminishing returns, creative fatigue vs frequency, noise.
- FR-2.3 Injected scenarios with ground truth: `creative_fatigue`, `audience_mismatch`, `landing_page_break`, `cpc_spike`, `channel_opportunity`, `tracking_break`, `budget_overpace`, plus no-issue windows.
- FR-2.4 Output modes: `backfill` (e.g. 180 days) and `batch` (next N days) for sequential uploads in demos.

### FR-3 Ingestion
- FR-3.1 `Connector` interface (`fetch(since, until)`); `CsvConnector` implemented; real API connectors are stubs.
- FR-3.2 Per-source schema templates with column mapping; row-level validation; rejected-row report.
- FR-3.3 Idempotent upsert on natural keys; ingestion runs logged.
- FR-3.4 Successful ingestion triggers the analysis pipeline for the new date range.
- FR-3.5 **As-of date** = latest complete day across required sources.

### FR-4 KPI / Semantic Layer
- FR-4.1 Metric registry from base measures: CTR, CPC, CPM, CVR, CPA, ROAS, AOV, frequency, bounce rate, funnel step rates.
- FR-4.2 Blended & profit metrics: **MER** (store revenue / total spend), contribution margin, profit-adjusted ROAS vs break-even ROAS.
- FR-4.3 Ratios always recomputed from base measures, never averaged.
- FR-4.4 Query by dimension (channel, campaign, ad set/audience, creative, device, region) × grain (day/week/month) with period comparison and goal comparison.
- FR-4.5 Decomposition definitions (`CPA = CPC / CVR`, `ROAS = CVR × AOV / CPC`, `CPC = CPM / (1000·CTR)`) for diagnosis.

### FR-5 Data Trust Checks
- FR-5.1 Freshness & completeness: missing days, missing sources, partial days.
- FR-5.2 **Tracking break detection:** platform-reported conversions diverge from store orders beyond historical ratio (e.g. Meta purchases −80 % while store orders flat).
- FR-5.3 Attribution gap: sum of platform-claimed conversions vs store orders, trended.
- FR-5.4 Trust status per source/day: `ok | warning | broken`.
- FR-5.5 **Gating:** performance recommendations on a `broken` source are suppressed and replaced by a "fix tracking first" item.

### FR-6 Signal Engine
- FR-6.1 Detectors: rolling-baseline % change, STL-adjusted robust z-score, change-point (ruptures), funnel divergence, cross-segment divergence, **goal breach** (metric vs target).
- FR-6.2 Types: performance, audience, creative, funnel, opportunity, goal.
- FR-6.3 Score = `magnitude × statistical_confidence × business_impact(₹) × recency_decay`; threshold before surfacing.
- FR-6.4 Suppression: festive windows (FR-1.5), minimum sample sizes, duplicates.
- FR-6.5 Each signal stores metric, slice, baseline, current, delta, score, window, detector.

### FR-7 Budget Pacing
- FR-7.1 Month-to-date spend vs plan per channel; projected month-end spend (run-rate).
- FR-7.2 Status `on_track | over | under` with tolerance; pacing signals feed the briefing.
- FR-7.3 Suggested daily spend to land on plan.

### FR-8 Investigation (LangGraph)
- FR-8.1 Cluster related signals into an **Opportunity** (entity + window + metric tree).
- FR-8.2 Deterministic metric decomposition → evidence tree with contribution %.
- FR-8.3 Retrieve similar past decisions (FR-12).
- FR-8.4 LLM structured output: `observation`, ranked `hypotheses[]` with `evidence_signal_ids[]`, `alternative_explanations[]`.
- FR-8.5 **Grounding guard:** all IDs and numbers must exist in the evidence set; retry with feedback (max 2) → rule-based fallback.
- FR-8.6 Observation, evidence, hypothesis stored and shown separately; never assert causality.

### FR-9 Recommendations
- FR-9.1 Typed **action catalogue**: `budget_shift`, `pause_creative`, `rotate_creative`, `retarget_audience`, `investigate_landing_page`, `fix_tracking`, `adjust_pacing`. LLM selects/parameterises; never invents types.
- FR-9.2 Each recommendation: problem, evidence, hypothesis, action, expected impact range, confidence, risk, KPI to monitor, stop condition.
- FR-9.3 **Computed confidence** = `f(statistical strength, # agreeing signals, decomposition share, data trust)`.
- FR-9.4 Guardrails from FR-1.6 enforced in code before display.
- FR-9.5 Priority = expected ₹ impact × confidence.

### FR-10 Simulator & Planner
- FR-10.1 Fit per-channel response curves (Hill/log) from history.
- FR-10.2 What-if: move budget → projected conversions, revenue, CPA, ROAS, MER with uncertainty band.
- FR-10.3 **Planner:** given monthly budget + goal, optimise allocation (`scipy.optimize`) within guardrails.
- FR-10.4 Budget recommendations include a simulation result.

### FR-11 Experiments (lite)
- FR-11.1 Create from a recommendation: hypothesis, action, primary metric, baseline, target, duration.
- FR-11.2 Approve / edit / reject via LangGraph `interrupt`; team applies the change on the platform themselves.
- FR-11.3 On later uploads covering the duration, evaluate **before vs after** on the primary metric; verdict `worked | did_not_work | inconclusive` (inconclusive if sample too small).
- FR-11.4 Progress view (day X / Y, metric so far).

### FR-12 Decision Memory (lite)
- FR-12.1 Store the chain: signals → hypothesis → recommendation → decision (+ reason) → outcome.
- FR-12.2 Similar-case lookup by signal pattern + entity type + action type; shown as history on opportunities.
- FR-12.3 Searchable decision timeline ("why did we pause that?").

### FR-13 Weekly Reports
- FR-13.1 Report data assembled **in code**: KPIs vs goals, week-over-week, pacing, top opportunities, decisions made, experiment results.
- FR-13.2 Two versions: **Founder** (5 lines: money, what changed, what we did, what's next) and **Team** (full detail).
- FR-13.3 LLM writes the narrative only; grounding guard verifies every number.
- FR-13.4 View, copy, export (Markdown / print-to-PDF); history of past reports.

### FR-14 Analyst (secondary chat)
- FR-14.1 ReAct agent with read-only tools: `query_metrics`, `get_signals`, `get_opportunity`, `get_pacing`, `get_trust_status`, `get_decision_history`, `run_simulation`.
- FR-14.2 Streams tokens + tool steps; answers cite metric/signal IDs.
- FR-14.3 Threads persisted via checkpointer.

### FR-15 Frontend
Screens, flows and layout are defined in `UI.md`; visual tokens in `designSystem.md`.

### FR-16 Evaluation
- FR-16.1 Detection precision / recall / F1 / latency vs ground truth.
- FR-16.2 Diagnosis top-1 / top-3 accuracy (LLM vs rule baseline).
- FR-16.3 Tracking-break detection accuracy; false-positive rate in no-issue windows.
- FR-16.4 Grounding violation rate pre/post guard.
- FR-16.5 Bedrock vs Gemini comparison.
- FR-16.6 User study: dashboard vs ChatGPT+CSV vs MDIA (time, correctness, evidence, action quality).

---

## 7. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 Accuracy | All numbers shown come from code; LLM text is grounding-checked. |
| NFR-2 Reproducibility | Same seed ⇒ same CSVs; same data ⇒ same deterministic output. |
| NFR-3 Traceability | Every claim links to metric/signal IDs; every LLM call logged (model, prompt version, tokens, latency, grounding result). |
| NFR-4 Provider independence | Bedrock → Gemini via env only; smoke test per provider. |
| NFR-5 Reliability | `RetryPolicy` on LLM nodes; rule-based fallback; pipeline never blocks on the LLM. |
| NFR-6 Performance | Pipeline for one uploaded day < 60 s; dashboard API p95 < 500 ms. |
| NFR-7 Testability | Pure `domain/` layer ≥ 80 % coverage; graphs tested with a fake LLM. |
| NFR-8 Security | Secrets in `.env` only; analyst tools read-only; parameterised SQL. |
| NFR-9 Cost | ₹0 infra (Neon free, local run); LLM cache by input hash for eval. |
| NFR-10 Usability | New user reaches first insight in < 5 min (onboarding → upload → Today). |

---

## 8. Future Requirements

| ID | Feature |
|---|---|
| F-1 | Morning brief & alerts via **WhatsApp / Slack / email** |
| F-2 | Real connectors: Google Ads, Meta Marketing API, GA4, Shopify (scheduled sync) |
| F-3 | Role-based views (founder vs marketer) and multi-user auth |
| F-4 | Feedback on recommendations (👍/👎 + reason) to learn team preferences |
| F-5 | Creative intelligence: fatigue forecast, winning hooks/formats, creative briefs |
| F-6 | Agency mode: multiple clients |
| F-7 | One-click apply actions to platforms (with approval) |

### Stretch (academic upgrades to FR-11/12)
| ID | Upgrade |
|---|---|
| S-1 | Control-group evaluation (difference-in-differences) to remove seasonality effects |
| S-2 | Action-aware generator: next batch CSV reacts to approved decisions |
| S-3 | Memory-driven confidence: historical success rate feeds FR-9.3 |

---

## 9. Data Model

| Table | Purpose |
|---|---|
| `business_profile`, `goals`, `budget_plans`, `calendar_events`, `guardrails` | FR-1 |
| `dim_channel`, `dim_campaign`, `dim_ad_set`, `dim_creative` | Entities |
| `fact_ad_daily` | date, channel, campaign, ad_set, creative, age_group, device, region, impressions, reach, clicks, spend, platform_conversions, platform_revenue |
| `fact_web_daily` | date, source, device, sessions, bounces, add_to_cart, checkout, purchases |
| `fact_store_daily` | date, orders, revenue, discounts, refunds, new_customers |
| `agg_metrics_daily` | Pre-aggregated KPIs per slice |
| `ingestion_runs` | Source, file, rows accepted/rejected, status |
| `trust_checks` | Source, date, check, status, detail |
| `pacing_snapshots` | Channel, month, MTD spend, projected, status |
| `signals` | FR-6.5 |
| `opportunities`, `hypotheses`, `recommendations` | FR-8, FR-9 |
| `simulations` | Inputs, projection, curve params |
| `experiments`, `experiment_results`, `decisions` | FR-11, FR-12 |
| `reports` | Week, version, payload (JSON), narrative, created_at |
| `llm_calls` | Node, model, prompt version, tokens, latency, grounding result |
| LangGraph checkpoint tables | `langgraph-checkpoint-postgres` |

---

## 10. Project Structure

```
capstone/
├── CLAUDE.md · requirements.md · task.md · UI.md · designSystem.md · README.md
├── .gitignore · .pre-commit-config.yaml
│
├── generator/                         # External CSV tool — "fake platforms"
│   ├── pyproject.toml
│   └── src/novawear_sim/
│       ├── config/                    # world.yaml, scenarios.yaml
│       ├── world/                     # entities, seasonality, saturation, fatigue
│       ├── scenarios/                 # one module per scenario
│       ├── exporters/                 # google_ads.py, meta_ads.py, web.py, store.py
│       ├── engine.py
│       └── cli.py                     # novawear-sim backfill | batch
│
├── backend/
│   ├── pyproject.toml · alembic.ini · .env.example
│   ├── migrations/
│   ├── src/mdia/
│   │   ├── main.py                    # app factory, lifespan
│   │   ├── core/                      # settings, logging, errors
│   │   ├── db/                        # engine, session, base
│   │   ├── models/                    # SQLAlchemy ORM, one file per aggregate
│   │   ├── schemas/                   # Pydantic API DTOs
│   │   ├── repositories/              # data access only
│   │   ├── domain/                    # PURE deterministic logic — no I/O, no LLM
│   │   │   ├── goals/                 # break-even ROAS, goal evaluation
│   │   │   ├── kpi/                   # registry, formulas, decomposition
│   │   │   ├── trust/                 # freshness, tracking-break, attribution gap
│   │   │   ├── signals/               # detectors, scoring, clustering
│   │   │   ├── pacing/
│   │   │   ├── diagnosis/             # evidence tree, rule-based diagnosis
│   │   │   ├── recommendations/       # action catalogue, confidence, guardrails
│   │   │   ├── simulation/            # response curves, optimizer
│   │   │   ├── experiments/           # before/after evaluation
│   │   │   └── reports/               # report payload assembly
│   │   ├── ingestion/
│   │   │   ├── connectors/            # base.py, csv.py, stubs/
│   │   │   ├── templates/             # per-source column schemas
│   │   │   └── validation.py
│   │   ├── services/                  # use cases: repos + domain + agents
│   │   ├── pipeline/                  # analysis pipeline run on ingestion
│   │   ├── agents/
│   │   │   ├── llm/                   # factory.py, roles
│   │   │   ├── prompts/               # versioned templates
│   │   │   ├── schemas/               # structured-output models
│   │   │   ├── guards/                # grounding validator
│   │   │   ├── tools/                 # analyst read-only tools
│   │   │   ├── nodes/                 # node functions per graph
│   │   │   ├── state.py
│   │   │   ├── checkpointer.py
│   │   │   └── graphs/                # briefing, investigation, experiment, report, analyst
│   │   └── api/
│   │       ├── deps.py
│   │       └── v1/routes/
│   └── tests/
│       ├── unit/ · integration/ · agents/
│
├── evaluation/                        # Only code that reads ground truth
│   ├── pyproject.toml
│   ├── src/mdia_eval/                 # detection, diagnosis, trust, grounding, providers, report
│   └── user_study/
│
├── frontend/
│   ├── components.json · vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── app/                       # router, providers, layout shell
│       ├── components/
│       │   ├── ui/                    # shadcn generated
│       │   └── common/                # KpiCard, Delta, ConfidenceMeter, TrustBadge, EmptyState
│       ├── features/                  # api.ts · hooks.ts · components/ · page.tsx each
│       │   ├── onboarding/ · today/ · opportunities/ · plan/ · experiments/
│       │   ├── reports/ · decisions/ · data/ · settings/ · analyst/
│       ├── lib/                       # api-client, query-keys, format (₹ lakh/crore, %), utils
│       └── types/api.ts               # generated from OpenAPI
│
└── docs/
    ├── architecture.md · decisions/ (ADRs) · thesis/
```

**Dependency rules**
- `api → services → (repositories, domain, agents)`; never reverse.
- `domain/` imports nothing from `db`, `api`, `agents`, LangChain.
- Only `agents/llm/factory.py` knows providers.
- Frontend features never import another feature's internals.

---

## 11. LangGraph Graphs

| Graph | Flow | Features |
|---|---|---|
| **briefing** | `load_signals → cluster → [Send] investigation × N → rank → persist` | `Send`, `operator.add` reducer |
| **investigation** | `load_context → decompose → retrieve_memory → hypothesise(LLM) → ground_check → (retry ⟲ \| fallback) → score_confidence → recommend(LLM) → apply_guardrails → simulate → persist` | Conditional edges, `RetryPolicy`, structured output |
| **experiment** | `draft → interrupt(approval) → track → evaluate → write_memory` | `interrupt` / `Command(resume)`, checkpointer |
| **report** | `assemble(code) → narrate(LLM) → ground_check ⟲ → persist` | Grounded narration |
| **analyst** | `agent ⇄ tools` | `ToolNode(handle_tool_errors=True)`, `stream_mode="messages"` |

---

## 12. API Surface (v1)

| Endpoint | Purpose |
|---|---|
| `GET/PUT /settings/profile`, `/settings/goals`, `/settings/budgets`, `/settings/calendar`, `/settings/guardrails` | FR-1 |
| `POST /ingestion/upload`, `GET /ingestion/runs`, `GET /ingestion/templates` | FR-3 |
| `GET /today` | Summary, trust banner, attention list, opportunities, pacing, active experiments |
| `GET /metrics` | KPI query |
| `GET /trust` | Trust status by source/day |
| `GET /pacing` | Month pacing per channel |
| `GET /signals` | Signals |
| `GET /opportunities`, `GET /opportunities/{id}`, `POST /opportunities/{id}/dismiss` | FR-8/9 |
| `POST /simulations`, `POST /simulations/plan` | FR-10 |
| `POST /experiments`, `POST /experiments/{id}/decision`, `GET /experiments[/{id}]` | FR-11 |
| `GET /decisions`, `GET /decisions/similar` | FR-12 |
| `POST /reports/weekly`, `GET /reports[/{id}]` | FR-13 |
| `POST /analyst/stream` | SSE chat |
| `GET /health` | DB + LLM provider |

---

## 13. Success Criteria

- ≥ 85 % of injected scenarios detected within 3 days of data; false-positive rate < 10 % on no-issue windows.
- Tracking breaks detected and performance recommendations correctly suppressed ≥ 90 %.
- Top-3 diagnosis accuracy ≥ 80 %.
- 0 ungrounded numbers in UI and reports (post-guard).
- Demo: onboarding → upload → Today → investigate → simulate → approve experiment → upload next batch → verdict → weekly report.
- Bedrock → Gemini via env only, with comparison in the evaluation report.
