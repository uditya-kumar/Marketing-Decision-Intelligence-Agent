# MDIA — Marketing Decision Intelligence Agent

A decision-intelligence system for marketing teams (final-semester capstone). Not a chatbot.

```
CSV exports → Trusted KPIs → Goal-aware signals → Evidence-backed diagnosis
            → Recommendation → Experiment → Outcome → Decision log
```

**Deterministic first:** metrics, detection, decomposition, trust checks, pacing, confidence
and experiment verdicts are code. The LLM only reasons over verified evidence and
writes narrative — it never produces a number shown to users.

## Packages

| Package | Purpose |
|---|---|
| `generator/` | Synthetic CSV tool — "fake" Meta / Google / GA4 / Shopify exports + `ground_truth.json` |
| `backend/` | FastAPI + LangGraph service (API, domain logic, agents) |
| `evaluation/` | The only code that reads `ground_truth.json` |
| `frontend/` | React 19 + Vite + TypeScript UI |

## Setup

Requires: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 20+, npm, and a
[Neon](https://neon.tech) Postgres project with a `dev` and a `test` branch.

```bash
# backend
cd backend
uv sync
cp .env.example .env          # Neon connection strings + LLM provider; never commit this
uv run alembic upgrade head   # creates the schema on the branch DATABASE_URL points at

# generator
cd ../generator
uv sync

# frontend
cd ../frontend
npm install
```

Without LLM credentials everything still works: diagnoses and the weekly report fall back to the
rule-based versions, labelled as such in the UI.

## Run

```bash
cd backend   && uv run uvicorn mdia.main:app --reload   # API on :8000, docs at /docs
cd frontend  && npm run dev                             # UI on :5173
```

Generate exports to feed it (seeded, so the output is reproducible):

```bash
cd generator
uv run novawear-sim backfill --days 180 --seed 42      # -> output/backfill/        (…2026-10-14)
uv run novawear-sim batch --from 2026-10-15 --days 7   # -> output/batch_2026-10-15/
```

Then open the UI, fill in **Settings**, and drop a folder's four CSVs on the **Data** page. Each
folder also holds a `ground_truth.json` — don't upload it; only `evaluation/` may read it.

## Demo

`docs/demo.md` is the runbook: four seeded weeks that walk from an upload to a logged decision with
a verdict and a weekly report — Meta over-pacing its budget, a fatiguing creative, Performance Max
headroom, and a tracking break that stops the system recommending anything until it is fixed.

## Checks

```bash
cd backend
uv run ruff format . && uv run ruff check . && uv run mypy src
uv run pytest -m "not integration"      # integration tests run against the Neon `test` branch
uv run pytest -m "not integration" --cov # domain coverage, gated at 80 %

cd frontend
npm run lint && npm run test && npm run build
npm run gen:api                          # regenerate src/types/api.ts from the running API
```

## Documentation

- `docs/architecture.md` — how it fits together: deterministic-first, trust gating, the grounding guard
- `docs/demo.md` — the demo runbook
- `requirements/requirements.md` — what to build (FR/NFR IDs, data model, structure, API)
- `requirements/task.md` — build order
- `requirements/UI.md` — screens, flows, layout
- `requirements/designSystem.md` — visual tokens
- `CLAUDE.md` — agent guide & house rules
