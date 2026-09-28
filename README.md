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

## Getting started

Requires: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 20+, npm.

```bash
# backend
cd backend
uv sync
cp .env.example .env          # fill in Neon + LLM values
uv run uvicorn mdia.main:app --reload

# generator (see generator/README.md)
cd generator
uv sync
uv run novawear-sim backfill --days 180 --seed 42      # -> output/backfill/
uv run novawear-sim batch --from 2026-10-15 --days 7   # -> output/batch_2026-10-15/

# frontend
cd frontend
npm install
npm run dev
```

## Documentation

- `requirements/requirements.md` — what to build (FR/NFR IDs, data model, structure, API)
- `requirements/task.md` — build order
- `requirements/UI.md` — screens, flows, layout
- `requirements/designSystem.md` — visual tokens
- `CLAUDE.md` — agent guide & house rules
- `docs/` — architecture and ADRs
