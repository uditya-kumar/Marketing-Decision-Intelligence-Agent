# CLAUDE.md — MDIA (Marketing Decision Intelligence Agent)

Final-semester capstone. A decision-intelligence system for marketing teams: CSV exports → trusted KPIs → goal-aware signals → evidence-backed hypotheses → recommendations → experiments → decision memory. **It is not a chatbot**; chat is a secondary side panel.

## Read first
- `requirements.md` — what to build (FR/NFR IDs, data model, structure, graphs, API)
- `task.md` — build order; work on the next unticked task, tick it when its "Done when" passes
- `UI.md` — screens, flows, layout
- `designSystem.md` — visual tokens; **must be followed** for all UI (if missing, ask before inventing styles)
- LangGraph code: use the `langgraph-fundamentals` skill (`.agents/skills/langgraph-fundamentals`)

## Stack
- Backend: Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2 (psycopg 3), Alembic, Neon Postgres
- Analytics: pandas, NumPy, SciPy, statsmodels, ruptures
- Agents: LangGraph + LangChain `init_chat_model`; provider via env (`LLM_PROVIDER=bedrock_converse` now, `google_genai` later)
- Frontend: React 19 + React Compiler, Vite, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, React Router, Recharts, React Flow
- Packages: `generator/` (synthetic CSV tool), `backend/`, `evaluation/`, `frontend/`

## Commands
```bash
# backend (run inside backend/)
uv sync
uv run uvicorn mdia.main:app --reload
uv run pytest -m "not integration"
uv run ruff check . && uv run ruff format . && uv run mypy src
uv run alembic revision --autogenerate -m "<msg>" && uv run alembic upgrade head

# generator (inside generator/)
uv run novawear-sim backfill --days 180 --seed 42
uv run novawear-sim batch --from 2026-10-15 --days 7

# frontend (inside frontend/)
npm run dev · npm run build · npm run lint · npm run test
npm run gen:api        # regenerate src/types/api.ts from OpenAPI
```
Environment: Windows + Git Bash. Use forward slashes.

## Core rule: deterministic first
Anything that can be computed **must be code**, not LLM. The LLM never produces a number that is shown to users.

| Code (in `domain/`) | LLM (in `agents/`) |
|---|---|
| KPIs, ratios, blended/profit metrics | Ranking and phrasing hypotheses from given evidence |
| Anomaly/change detection, scoring | Choosing an action **from the catalogue** and its rationale |
| Metric decomposition / evidence tree | Alternative explanations |
| Data trust checks, pacing, goal status | Report and briefing narrative |
| Confidence score, priority, guardrails | Analyst chat answers (via read-only tools) |
| Simulation, optimisation, experiment verdicts | |

- LLM output uses **structured output** (Pydantic schema), temperature 0.
- Every LLM output passes `agents/guards/grounding.py`: IDs and numbers must exist in the provided evidence. On failure: retry with feedback (max 2), then rule-based fallback.
- LLM nodes get a `RetryPolicy`; the pipeline must never block on the LLM.

## Architecture & separation of concerns
```
api/ → services/ → repositories/ | domain/ | agents/
```
- `api/v1/routes/` — HTTP only: parse, call one service, return schema. No logic.
- `services/` — use cases; orchestrate repos, domain, agents; own transactions.
- `repositories/` — DB queries only; return ORM/DTOs; no business rules.
- `domain/` — **pure functions/classes**: no DB, no HTTP, no LangChain, no env reads. Fully unit-tested.
- `agents/` — LangGraph graphs, nodes, prompts, tools, guards. Nodes call services/domain for data and never touch the DB directly.
- `agents/llm/factory.py` is the **only** file that knows about LLM providers.
- `models/` (ORM) ≠ `schemas/` (API DTOs) ≠ `agents/schemas/` (LLM structured output). Don't mix them.
- **The backend never reads `ground_truth.json`.** Only `evaluation/` does.
- Frontend: feature folders (`features/<name>/{api.ts,hooks.ts,components/,page.tsx}`); features don't import each other's internals; shared code goes in `components/common` or `lib/`. `components/ui/` is shadcn-generated, so don't hand-edit it.

## Code style
- Small files, one responsibility each; split when a file passes ~200 lines or does two things.
- Python: full type hints (mypy clean), Ruff formatting, `snake_case`, Pydantic models at boundaries, dataclasses/`TypedDict` inside. Prefer pure functions. No bare `except`. Raise domain errors from `core/errors.py`, mapped to HTTP in one place.
- LangGraph: state as `TypedDict` with reducers for list fields; nodes return partial updates; one graph per file in `agents/graphs/`; node functions in `agents/nodes/<graph>/`; prompts versioned in `agents/prompts/`.
- TypeScript: strict mode; types generated from OpenAPI (don't hand-write API types); server state via TanStack Query only; no `any`; components are small and presentational where possible, with data in `hooks.ts`.
- UI: tokens from `designSystem.md` only (no ad-hoc colours or spacing); follow the section order and patterns in `UI.md`; every screen has empty, loading and error states.
- Naming follows the domain: `opportunity`, `signal`, `hypothesis`, `recommendation`, `experiment`, `decision`, `trust_check`, `pacing`.
- Comments explain *why*, not *what*. No dead code or commented-out blocks.
- Tests: unit tests for every `domain/` function (include property tests for KPI math); graphs tested with the fake LLM; integration tests run on the Neon `test` branch.

## Don'ts
- Don't let the LLM calculate, invent metrics, invent action types, or assert causality.
- Don't put business logic in routes, repositories, React components, or prompts.
- Don't average ratio metrics; recompute them from base measures.
- Don't commit `.env`, generated CSVs, or secrets.
- Don't build notifications or real platform connectors (future scope).
- Don't make chat the homepage.
