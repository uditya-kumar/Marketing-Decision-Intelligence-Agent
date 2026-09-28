# MDIA — Marketing Decision Intelligence Agent

> Dashboards tell marketers what happened. Chatbots answer what marketers ask.
> MDIA knows your goals, spots what matters, checks the data can be trusted, investigates why, recommends what to do, and checks whether it worked.

Companion docs: `task.md` (build plan) · `UI.md` (flows & layout) · `designSystem.md` (visual tokens) · `CLAUDE.md` (agent guide)

---

## 1. Problem Statement

Marketing data is spread across ad platforms, web analytics and the store. Every week a marketer compares tabs by hand to work out **what changed, whether the data is even correct, why it changed, and what to do**. Decisions and their outcomes get lost in chat threads.

General-purpose LLMs only analyse data when someone supplies it and asks the right question. They don't know the company's goals, don't check data integrity, don't remember decisions and don't verify outcomes.

MDIA is a decision-support system:

`CSV exports → Trusted KPIs → Goal-aware signals → Evidence-backed diagnosis → Recommendation → Experiment → Outcome → Decision log`

**Deterministic first.** Metrics, detection, decomposition, trust checks, pacing, confidence and experiment verdicts are all code. The LLM only reasons over verified evidence and writes narrative, and a guard checks its output.

---

## 2. Users

| Persona | Needs | Primary screens |
|---|---|---|
| **Founder** | "Are we making money? Is anything on fire?" | Today, Reports |
| **Performance marketer** | "What should I fix, kill or scale, and why?" | Today, Opportunity, Experiments |

A single-company, single-user app. There is no auth.

---

## 3. Scope

### In scope
- A synthetic D2C brand, **NovaWear** (Indian fashion e-commerce), with Google Ads, Meta Ads, web analytics and store orders.
- **CSV upload** in platform-export shape as the only ingestion path.
- Settings (margin, targets, budgets), profit-aware KPIs, data trust checks and budget pacing.
- Analysis on every upload → opportunities → LLM diagnosis with a grounding guard and a rules fallback → recommendation from a fixed catalogue.
- Lite experiments (approve → before/after verdict) and a decision log.
- A weekly report.
- Quantitative evaluation against the generator's ground truth.

### Out of scope
Real platform APIs, notifications, auth and multi-tenancy, auto-applying changes, budget optimisation, and chat. The simulator and chat are stretch goals (§8).

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, uv, FastAPI, Pydantic v2 |
| Database | **Neon Postgres** (branches `main` / `dev` / `test`), SQLAlchemy 2 (psycopg 3), Alembic |
| Analytics | pandas, NumPy, SciPy |
| Agents | **LangGraph** (StateGraph, conditional edges, RetryPolicy) |
| LLM | LangChain `init_chat_model` + `with_structured_output`; **Bedrock** now, **Gemini** by env switch |
| Background work | FastAPI `BackgroundTasks` (analysis runs after an upload) |
| Testing | pytest, Hypothesis, a fake chat model |
| Quality | Ruff, mypy, pre-commit, ESLint, Prettier |
| Frontend | React 19 + React Compiler, Vite, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, React Router, Recharts |

```env
LLM_PROVIDER=bedrock_converse        # or google_genai
LLM_MODEL=<model-id>
LLM_TEMPERATURE=0
```

`agents/llm.py` is the only file that knows about providers.

---

## 5. Architecture

```
generator/ (CLI) ──► platform-shaped CSVs + ground_truth.json
                           │ user uploads CSVs
                           ▼
                ┌──────────────────────┐
                │ Ingestion            │  detect source → validate rows → upsert
                └──────────┬───────────┘
                           ▼  background task
┌──────────┐    ┌──────────────────────────────────────────────┐
│ Settings │───►│ Analysis (code)                              │
│ goals,   │    │ KPIs → trust (gates) → pacing → signals      │
│ budgets  │    │ → opportunities                              │
└──────────┘    └──────────┬───────────────────────────────────┘
                           ▼  top N opportunities
                ┌──────────────────────────────────────────────┐
                │ LangGraph investigation                      │
                │ evidence(code) → diagnose(LLM) → ground check│
                │ ⟲ retry ≤2 | rules fallback → finalize(code) │
                └──────────┬───────────────────────────────────┘
                           ▼
        Opportunities · Experiments · Decision log · Weekly report
```

**Rule:** the backend never reads ground truth. Only `evaluation/` joins system output with `ground_truth.json`.

---

## 6. Functional Requirements

### FR-1 Settings
- FR-1.1 A single settings record holding the business name, gross margin %, target CPA, target ROAS, and monthly budget per channel.
- FR-1.2 Derived **break-even ROAS** (`1 / margin`).
- FR-1.3 Festive/sale windows (date ranges) where big changes are expected.
- FR-1.4 Protected campaigns, which are never recommended for pausing.

### FR-2 Synthetic Data Generator ✅
- A seeded, deterministic CLI that writes `google_ads.csv`, `meta_ads.csv`, `web_analytics.csv` and `store_orders.csv` in realistic export shapes.
- It models seasonality, festive spikes, diminishing returns, creative fatigue and noise.
- It injects scenarios with ground truth: `creative_fatigue`, `audience_mismatch`, `landing_page_break`, `cpc_spike`, `channel_opportunity`, `tracking_break` and `budget_overpace`, plus no-issue windows.
- Two modes: `backfill` and `batch` (the next N days, for sequential demo uploads).

### FR-3 Ingestion
- FR-3.1 Per-source column templates; the source is detected from the headers.
- FR-3.2 Row-level validation with a rejected-row report.
- FR-3.3 Idempotent upsert on natural keys; every run is logged.
- FR-3.4 A successful upload triggers the analysis in the background.
- FR-3.5 **As-of date** = the latest day covered by every source.

### FR-4 KPIs
- FR-4.1 Computed from base measures: CTR, CPC, CPM, CVR, CPA, ROAS, AOV, frequency, bounce rate, and **MER** (store revenue / total ad spend).
- FR-4.2 Ratios are always recomputed from summed base measures and never averaged.
- FR-4.3 Queries by channel / campaign / ad set / creative / age group per day, compared with the previous period and with goals.
- FR-4.4 Decomposition (`CPA = CPC / CVR`, `ROAS = CVR × AOV / CPC`, `CPC = CPM / (1000·CTR)`) with log-change attribution for diagnosis.

### FR-5 Data Trust
- FR-5.1 Freshness: missing days and missing sources.
- FR-5.2 **Tracking break:** platform-reported conversions diverge from store orders beyond the channel's historical ratio.
- FR-5.3 Status per source: `ok | warning | broken`.
- FR-5.4 **Gating:** no performance signals on a `broken` source; a "fix tracking first" opportunity is raised instead.

### FR-6 Signals & Opportunities
- FR-6.1 Detectors:
  - rolling-baseline change, with a minimum-sample guard;
  - goal breach (metric vs target);
  - funnel-step drop;
  - segment divergence (age group within an ad set).
- FR-6.2 Score = `|Δ| × ₹ impact`, with a threshold before anything is surfaced; festive windows are suppressed.
- FR-6.3 Each signal stores its ID, detector, metric, entity, window, baseline, current value, delta and score.
- FR-6.4 Signals are grouped by entity + window into an **opportunity**, with a stable key so re-running doesn't duplicate it.

### FR-7 Budget Pacing
- Month-to-date spend vs budget per channel.
- Run-rate projection.
- Status `on_track | over | under`.
- Suggested daily spend to finish the month on plan.

### FR-8 Investigation (LangGraph)
- FR-8.1 An evidence tree built in code from the decomposition, with a contribution % per driver.
- FR-8.2 LLM structured output:
  - `observation`;
  - ranked `hypotheses[]`, each with a cause from a fixed list and `evidence_signal_ids[]`;
  - `alternative_explanations[]`;
  - a chosen `action_type` from the catalogue, with its rationale.
- FR-8.3 **Grounding guard:** every ID, action type and number must exist in the evidence. On failure it retries with feedback (at most 2 times), then falls back to the rule-based diagnosis.
- FR-8.4 What happened, the evidence and the likely cause are stored and shown separately. The system never asserts causality.

### FR-9 Recommendations
- FR-9.1 Action catalogue: `pause_creative`, `rotate_creative`, `refine_audience`, `investigate_landing_page`, `fix_tracking`, `shift_budget`, `adjust_pacing`.
- FR-9.2 Each recommendation carries the action, expected impact range (computed), confidence, risk, KPI to watch, and a stop condition.
- FR-9.3 **Computed confidence** = `f(signal strength, # agreeing signals, decomposition share, data trust)`.
- FR-9.4 The protected-campaign guardrail is enforced in code. Priority = ₹ impact × confidence.

### FR-10 Experiments & Decision Log
- FR-10.1 Create an experiment from a recommendation, auto-filled with hypothesis, action, metric, baseline, target and duration. The team makes the change on the platform themselves.
- FR-10.2 Approve / reject / dismiss, each with an optional reason, writes a decision.
- FR-10.3 Once later uploads cover the duration, the experiment gets a **before vs after** verdict: `worked | did_not_work | inconclusive` (inconclusive if the sample is too small).
- FR-10.4 The decision log shows each decision with its chain: opportunity → experiment → outcome.

### FR-11 Weekly Report
- FR-11.1 The payload is built in code: KPIs vs goals, week-on-week change, pacing, top opportunities, decisions and experiment results.
- FR-11.2 The LLM writes a short founder summary and a team section; the grounding guard checks every number, with a template fallback.
- FR-11.3 View, copy as Markdown, print; plus a history of past reports.

### FR-12 Frontend
Screens and flows are in `UI.md`, visual tokens in `designSystem.md`.

### FR-13 Evaluation
- FR-13.1 Detection precision / recall / F1 / days-to-detect vs ground truth; false positives in no-issue windows.
- FR-13.2 Diagnosis top-1 / top-3 accuracy, LLM vs rules.
- FR-13.3 Tracking-break detection and suppression accuracy.
- FR-13.4 Grounding violation rate before and after the guard.

---

## 7. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 Accuracy | Every number shown comes from code; LLM text is grounding-checked. |
| NFR-2 Reproducibility | Same seed ⇒ same CSVs; same data ⇒ same deterministic output. |
| NFR-3 Traceability | Claims link to signal IDs; every LLM call is logged (model, prompt version, latency, tokens, grounded, fallback). |
| NFR-4 Provider independence | Switching Bedrock → Gemini needs env changes only. |
| NFR-5 Reliability | `RetryPolicy` on LLM nodes plus the rules fallback, so the analysis never blocks on the LLM. |
| NFR-6 Performance | Dashboard endpoints < 500 ms on the 180-day dataset. |
| NFR-7 Testability | `domain/` ≥ 80 % coverage; graphs tested with a fake LLM. |
| NFR-8 Security | Secrets only in `.env`; parameterised SQL. |
| NFR-9 Cost | ₹0 infrastructure (Neon free tier, runs locally). |

---

## 8. Future Work & Stretch

**Future (not built):** real connectors (Google Ads, Meta, GA4, Shopify), WhatsApp/Slack alerts, multi-user auth and roles, one-click apply to platforms, and creative intelligence.

**Stretch (only if time allows):** see `task.md`. Budget simulator, analyst chat, provider comparison, difference-in-differences verdicts, an action-aware generator, and a user study.

---

## 9. Data Model

| Table | Purpose |
|---|---|
| `settings` | Single row (FR-1); budgets, festive windows and protected campaigns as JSONB |
| `dim_channel`, `dim_campaign`, `dim_ad_set`, `dim_creative` | Entities |
| `fact_ad_daily` | date, creative, age_group, device, region → impressions, reach, clicks, spend, platform_conversions, platform_revenue |
| `fact_web_daily` | date, source, device → sessions, bounces, add_to_cart, checkout, purchases, revenue |
| `fact_store_daily` | date → orders, revenue, discounts, refunds, new_customers |
| `ingestion_runs` | Source, file, rows accepted/rejected, rejected-row sample, status |
| `analysis_runs` | Status, as-of date, counts, error |
| `opportunities` | Key, kind, entity, window, status; signals / evidence / diagnosis / recommendation as JSONB; confidence, priority, diagnosis source (`llm \| rules`) |
| `experiments` | Opportunity, action, metric, baseline, target, dates, status, verdict, before/after values |
| `decisions` | Kind (approve / reject / dismiss), reason, opportunity, experiment, timestamp |
| `reports` | Week, payload (JSONB), narrative, grounded, created_at |
| `llm_calls` | Purpose, model, prompt version, tokens, latency, attempts, grounded, fallback |

KPIs, trust status and pacing are computed on request. They are not stored.

---

## 10. Project Structure

```
capstone/
├── CLAUDE.md · README.md · requirements/ · docs/
├── generator/                    # External CSV tool ("fake platforms") ✅
│
├── backend/
│   ├── migrations/
│   ├── src/mdia/
│   │   ├── main.py               # app factory, error mapping
│   │   ├── core/                 # settings, logging, errors
│   │   ├── db/                   # engine, session, Base
│   │   ├── models/               # ORM, one file per aggregate
│   │   ├── schemas/              # API DTOs
│   │   ├── repositories/         # queries only
│   │   ├── domain/               # PURE logic, one module per concept:
│   │   │                         #   sources, goals, kpi, decomposition, trust, pacing,
│   │   │                         #   signals, opportunities, diagnosis, recommendations,
│   │   │                         #   experiments, reports
│   │   ├── ingestion/            # parsers, templates, validation, reader
│   │   ├── services/             # use cases (ingestion, settings, metrics, analysis, …)
│   │   ├── agents/               # llm.py, schemas.py, prompts.py, grounding.py,
│   │   │                         #   investigation.py, report.py
│   │   └── api/                  # deps.py, router.py, routes/
│   └── tests/                    # unit/ · integration/ · fixtures/ · fakes.py
│
├── evaluation/                   # the only code that reads ground truth
│   └── src/mdia_eval/            # run schedule, detection, diagnosis, trust, grounding, report
│
└── frontend/src/
    ├── app/                      # router, providers, layout shell
    ├── components/ui/            # shadcn generated
    ├── components/common/        # KpiCard, Delta, TrustBadge, ConfidenceMeter, AiBlock, EmptyState
    ├── features/<name>/          # api.ts (fetchers + query hooks) · page.tsx · components/
    │                             #   today, opportunities, experiments, decisions, reports, data, settings
    ├── lib/                      # api-client, format (₹ lakh/crore, %), utils
    └── types/api.ts              # generated from OpenAPI
```

**Dependency rules:**
- `api → services → (repositories, domain, agents)`, never the reverse.
- `domain/` imports nothing from `db`, `api`, `agents` or LangChain.
- Features never import from each other.

---

## 11. LangGraph Graphs

| Graph | Flow | Features used |
|---|---|---|
| **investigation** | `build_evidence → diagnose(LLM) → ground_check → (retry ⟲ \| rules_fallback) → finalize` | TypedDict state, conditional edges, `RetryPolicy`, structured output |
| **report** | `narrate(LLM) → ground_check → (retry ⟲ \| template_fallback)` | Grounded narration |

The service runs the graphs one opportunity at a time. There is no fan-out and no checkpointer.

---

## 12. API Surface (`/api/v1`)

| Endpoint | Purpose |
|---|---|
| `GET /health` (root) | DB + LLM provider |
| `GET/PUT /settings` | FR-1 |
| `POST /ingestion/upload`, `GET /ingestion/runs`, `GET /ingestion/status`, `GET /ingestion/templates` | FR-3 |
| `GET /analysis/status` | Latest analysis run |
| `GET /today` | KPIs, trust, pacing, top opportunities, active experiments |
| `GET /metrics` | KPI series for charts |
| `GET /trust` | Trust status per source |
| `GET /opportunities`, `GET /opportunities/{id}`, `POST /opportunities/{id}/dismiss` | FR-6/8/9 |
| `POST /experiments`, `POST /experiments/{id}/approve`, `POST /experiments/{id}/reject`, `GET /experiments` | FR-10 |
| `GET /decisions` | FR-10.4 |
| `POST /reports/weekly`, `GET /reports`, `GET /reports/{id}` | FR-11 |

---

## 13. Success Criteria

- ≥ 80 % of injected scenarios detected within 3 days of data; false-positive rate < 10 % on no-issue windows.
- Tracking breaks detected and performance advice suppressed in ≥ 90 % of cases.
- Top-3 diagnosis accuracy ≥ 80 %.
- 0 ungrounded numbers in the UI and reports after the guard.
- Demo: upload → Today → open an opportunity → create and approve an experiment → upload next week → verdict → weekly report.
