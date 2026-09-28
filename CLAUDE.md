# CLAUDE.md — MDIA (Marketing Decision Intelligence Agent)

Final-semester capstone (one student, one semester — keep it that size). A decision-intelligence system for marketing teams: CSV exports → trusted KPIs → goal-aware signals → evidence-backed diagnosis → recommendation → experiment → decision log. **It is not a chatbot**; there is no chat in the core scope.

**Keep it simple.** Build only what `task.md` lists; prefer a flat module over a package, a function over a class, a JSONB column over an extra table, and computing on request over storing. Stretch items stay out until the core demo works.

## Read first
- `requirements/requirements.md` — what to build (FR/NFR IDs, data model, structure, graphs, API)
- `requirements/task.md` — build order; work on the next unticked task, tick it when its "Done when" passes
- `requirements/UI.md` — screens, flows, layout; layouts in `requirements/designFile.pen` (pencil MCP only)
- `requirements/designSystem.md` — visual tokens; **must be followed** for all UI (if missing, ask before inventing styles)
- LangGraph code: use the `langgraph-fundamentals` skill (`.agents/skills/langgraph-fundamentals`)

## Stack
- Backend: Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2 (psycopg 3), Alembic, Neon Postgres
- Analytics: pandas, NumPy, SciPy
- Agents: LangGraph + LangChain `init_chat_model`; provider via env (`LLM_PROVIDER=bedrock_converse` now, `google_genai` later)
- Frontend: React 19 + React Compiler, Vite, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, React Router, Recharts
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
| KPIs, ratios, MER, break-even ROAS | Ranking and phrasing hypotheses from given evidence |
| Change detection, scoring, opportunities | Choosing an action **from the catalogue** and its rationale |
| Metric decomposition / evidence tree | Alternative explanations |
| Data trust checks, pacing, goal status | Weekly report narrative |
| Confidence, priority, guardrails, experiment verdicts | |

- LLM output uses **structured output** (Pydantic schema), temperature 0.
- Every LLM output passes `agents/grounding.py`: IDs and numbers must exist in the provided evidence. On failure: retry with feedback (max 2), then rule-based fallback.
- LLM nodes get a `RetryPolicy`; the analysis must never block on the LLM.

## Architecture & separation of concerns
```
api/ → services/ → repositories/ | domain/ | agents/
```
- `api/routes/` — HTTP only: parse, call one service, return schema. No logic.
- `services/` — use cases; orchestrate repos, domain, agents; own transactions.
- `repositories/` — DB queries only; return ORM/DTOs; no business rules.
- `domain/` — **pure functions**, one flat module per concept (`kpi.py`, `trust.py`, `signals.py`, …): no DB, no HTTP, no LangChain, no env reads. Fully unit-tested.
- `agents/` — flat: `llm.py`, `schemas.py`, `prompts.py`, `grounding.py`, one file per graph (`investigation.py`, `report.py`). Nodes get their data passed in and never touch the DB.
- `agents/llm.py` is the **only** file that knows about LLM providers.
- `models/` (ORM) ≠ `schemas/` (API DTOs) ≠ `agents/schemas.py` (LLM structured output). Don't mix them.
- **The backend never reads `ground_truth.json`.** Only `evaluation/` does.
- Frontend: feature folders (`features/<name>/{api.ts,page.tsx,components/}`; `api.ts` holds fetchers + TanStack Query hooks); features don't import each other's internals; shared code goes in `components/common` or `lib/`. `components/ui/` is shadcn-generated, so don't hand-edit it.

## Code style
- Small files, one responsibility each; split when a file passes ~200 lines or does two things.
- Python: full type hints (mypy clean), Ruff formatting, `snake_case`, Pydantic models at boundaries, dataclasses/`TypedDict` inside. Prefer pure functions. No bare `except`. Raise domain errors from `core/errors.py`, mapped to HTTP in one place.
- LangGraph: state as `TypedDict`; nodes return partial updates; the graph and its nodes live in one file; prompts carry a version constant in `agents/prompts.py`. No checkpointer, no `Send` fan-out.
- TypeScript: strict mode; types generated from OpenAPI (don't hand-write API types); server state via TanStack Query only; no `any`; components are small and presentational where possible, with data hooks in `api.ts`.
- UI: tokens from `designSystem.md` only (no ad-hoc colours or spacing); follow the section order and patterns in `UI.md`; every screen has empty, loading and error states.
- Naming follows the domain: `opportunity`, `signal`, `hypothesis`, `recommendation`, `experiment`, `decision`, `trust`, `pacing`.
- Comments explain *why*, not *what*. No dead code or commented-out blocks.
- Tests: unit tests for every `domain/` function (include property tests for KPI math); graphs tested with the fake LLM (`tests/fakes.py`); integration tests run on the Neon `test` branch — they are slow, so ask before running the whole suite.

## Don'ts
- Don't let the LLM calculate, invent metrics, invent action types, or assert causality.
- Don't put business logic in routes, repositories, React components, or prompts.
- Don't average ratio metrics; recompute them from base measures.
- Don't commit `.env`, generated CSVs, or secrets.
- Don't build notifications or real platform connectors (future scope).
- Don't add chat, a simulator/planner, a command palette, dark mode or other stretch items unless the user asks.
