# MDIA — Marketing Decision Intelligence Agent

Turns marketing CSV exports into evidence-backed decisions: trusted KPIs, a diagnosed cause, a recommended action, and an experiment that proves whether it worked.

## Tech stack

| Layer | Stack |
|---|---|
| **Backend** | ![Python](https://img.shields.io/badge/Python%203.12-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic%20v2-E92063?logo=pydantic&logoColor=white) |
| **Database** | ![Postgres](https://img.shields.io/badge/Neon%20Postgres-4169E1?logo=postgresql&logoColor=white) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy%202-D71F00?logo=sqlalchemy&logoColor=white) ![Alembic](https://img.shields.io/badge/Alembic-6BA81E) |
| **Analytics** | ![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white) ![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?logo=scipy&logoColor=white) |
| **Agents** | ![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langgraph&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white) ![Bedrock](https://img.shields.io/badge/Amazon%20Bedrock-232F3E) |
| **Frontend** | ![React](https://img.shields.io/badge/React%2019-61DAFB?logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind%20v4-06B6D4?logo=tailwindcss&logoColor=white) ![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-000000?logo=shadcnui&logoColor=white) ![TanStack Query](https://img.shields.io/badge/TanStack%20Query-FF4154?logo=reactquery&logoColor=white) ![Recharts](https://img.shields.io/badge/Recharts-22B5BF?logo=chartdotjs&logoColor=white) |
| **Tooling** | ![uv](https://img.shields.io/badge/uv-DE5FE9?logo=uv&logoColor=white) ![Ruff](https://img.shields.io/badge/Ruff-D7FF64?logo=ruff&logoColor=black) ![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white) ![Vitest](https://img.shields.io/badge/Vitest-6E9F18?logo=vitest&logoColor=white) |

---

## What it does

Every Monday a marketing team exports last week's CSVs and asks the same four questions. MDIA
answers them in order:

```
Upload CSVs  →  What changed?  →  Why?  →  What should I do?  →  Did it work?
```

A dashboard shows you numbers and leaves the thinking to you. MDIA picks out the changes that
matter against your goals, explains each one with computed evidence, recommends one action, then
measures it a week later and writes the outcome down.

**It is not a chatbot** — there is no chat. And the LLM never produces a number you see; those are
all computed in code.

## Features

- **CSV ingestion** — detects each platform from its headers, validates every row, and reports the
  rejected ones individually instead of failing the file.
- **Data-trust gating** — checks whether a source can be believed this week (platform conversions
  against store orders, metric drift). A broken source greys out its KPIs and **suppresses** its
  signals, so the system never recommends a budget cut on a measurement artefact.
- **Goal-aware signals** — change detection against baselines, targets and monthly pacing, not
  fixed thresholds. Scored and ranked by rupee impact, so a 40 % swing on a tiny ad set doesn't
  outrank a 5 % swing on the main campaign.
- **Evidence tree** — metric decomposition on the way down: CPA moved because CPC moved because
  CPM moved, with each contribution's share of the total. Computed, and the shares sum to 100 %.
- **Grounded diagnosis** — the LLM ranks and phrases hypotheses over that evidence. Every ID and
  number in its answer is checked against the evidence before display; if one is invented, it
  retries, then falls back to the rule-based diagnosis and says so on screen.
- **Recommendation** — one action from a fixed catalogue with its parameters, a computed
  confidence, a risk level and a stop condition. The model chooses from the list; it cannot invent
  an action.
- **Experiments** — approve a recommendation and it becomes a 7-day test with a baseline, a target
  and a metric, all pre-filled. Next week's upload evaluates it automatically: worked, didn't work,
  or inconclusive, with a minimum-sample guard so a two-day fluke never reads as a win.
- **Decision log** — every approval, rejection and dismissal recorded with its reason and its
  outcome. This is the artefact a team keeps; a dashboard has nothing like it.
- **Weekly report** — a founder summary over team detail, narrated by the LLM from the computed
  payload, with a templated version carrying the same numbers if the narrative fails its check.
- **Synthetic data + evaluation** — a seeded generator produces realistic exports with injected
  scenarios and a `ground_truth.json`, and a separate suite scores detection, diagnosis and false
  alarms against it.

## Packages

| Package | Purpose |
|---|---|
| `generator/` | Synthetic CSV tool — Meta / Google / GA4 / Shopify-shaped exports + `ground_truth.json` |
| `backend/` | FastAPI + LangGraph service (API, domain logic, agents) |
| `evaluation/` | Accuracy suite — the only code allowed to read `ground_truth.json` |
| `frontend/` | React 19 + Vite + TypeScript UI |

## Setup

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), Node 20+, and a [Neon](https://neon.tech)
Postgres project with a `dev` and a `test` branch.

```bash
cd backend
uv sync
cp .env.example .env          # Neon connection strings + LLM provider; never commit this
uv run alembic upgrade head   # creates the schema on the branch DATABASE_URL points at

cd ../generator
uv sync

cd ../frontend
npm install
```

Without LLM credentials everything still works: diagnoses and the weekly report fall back to the
rule-based versions, labelled as such in the UI.

## Run

Two terminals:

```bash
cd backend
uv run uvicorn mdia.main:app --reload    # API on :8000, OpenAPI docs at /docs
```

```bash
cd frontend
npm run dev                              # UI on :5173
```

Generate exports to feed it — seeded, so the output is reproducible:

```bash
cd generator
uv run novawear-sim backfill --days 180 --seed 42      # -> output/backfill/        (…2026-10-14)
uv run novawear-sim batch --from 2026-10-15 --days 7   # -> output/batch_2026-10-15/
```

Then open the UI, fill in **Settings** — margin, target CPA and ROAS, monthly goals and budgets —
and drop a folder's four CSVs on the **Data** page. Each folder also holds a `ground_truth.json`;
don't upload it, only `evaluation/` may read it.

Nothing is cached locally: uploads are parsed into fact rows in Postgres and everything you see is
read back from there.

## Demo

`docs/demo.md` is the runbook — four seeded weeks that walk from an upload to a logged decision
with a verdict and a weekly report: Meta over-pacing its budget, a fatiguing creative, Performance
Max headroom, and a tracking break that stops the system recommending anything until it is fixed.

Reset between runs with `uv run alembic downgrade base && uv run alembic upgrade head`.

## Checks

```bash
cd backend
uv run ruff format . && uv run ruff check . && uv run mypy src
uv run pytest -m "not integration"          # integration tests run against the Neon `test` branch
uv run pytest -m "not integration" --cov    # domain coverage, gated at 80 %

cd frontend
npm run lint && npm run test && npm run build
npm run gen:api                             # regenerate src/types/api.ts from the running API
```

## Documentation

| File | What's in it |
|---|---|
| `docs/architecture.md` | How it fits together: deterministic-first, trust gating, the grounding guard |
| `docs/demo.md` | The demo runbook, with measured timings |
| `docs/slides.md` | Presentation deck (Marp) |
| `requirements/requirements.md` | What to build — FR/NFR IDs, data model, structure, API |
| `requirements/task.md` | Build order |
| `requirements/UI.md` | Screens, flows, layout |
| `requirements/designSystem.md` | Visual tokens |
| `CLAUDE.md` | Agent guide and house rules |

---

Final-semester capstone project.
