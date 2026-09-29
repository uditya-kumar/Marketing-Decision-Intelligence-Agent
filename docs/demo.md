# Demo — the Monday morning story

Twelve minutes, four uploads, one decision that comes back with a verdict:

```
upload → Today → open an opportunity → create and approve an experiment
       → upload next week → verdict → weekly report
```

The data is seeded (`--seed 42`, `--schedule demo`), so the same commands in the same order
always produce the same screens. The weeks in the seeded data run Thursday to Wednesday —
"Monday morning" is the ritual of uploading last week's exports, not a date on screen.

---

## Before you start

### 1. Generate the four windows

```bash
cd generator
uv run novawear-sim backfill --days 180 --seed 42      # -> output/backfill/        (…2026-10-14)
uv run novawear-sim batch --from 2026-10-15 --days 7   # -> output/batch_2026-10-15/
uv run novawear-sim batch --from 2026-10-22 --days 7   # -> output/batch_2026-10-22/
uv run novawear-sim batch --from 2026-10-29 --days 7   # -> output/batch_2026-10-29/
```

Each folder holds `google_ads.csv`, `meta_ads.csv`, `web_analytics.csv`, `store_orders.csv` and
a `ground_truth.json`. Upload the four CSVs only — the labels belong to `evaluation/`, and the
backend is not allowed to read them.

What the `demo` schedule puts in those windows (`generator/src/novawear_sim/config/scenarios.yaml`):

| Event | When | What it is |
|---|---|---|
| `demo_05` | 22 Sep, 40 days | Performance Max has headroom — a win, not a problem |
| `demo_06` | all October, ×1.38 | Meta Ads over-pacing its monthly budget |
| `demo_07` | 4–18 Oct | the `ig_interest_c1` creative fatiguing, then rotated |
| `demo_08` | 24–30 Oct | Meta's conversion tracking breaks |

### 2. Empty the database

```bash
cd backend
uv run alembic downgrade base && uv run alembic upgrade head
```

That drops every table, so point `DATABASE_URL` at a Neon branch kept for the demo (or reset that
branch from its parent in the Neon console) rather than at a branch anyone else is using.

### 3. Start both halves

```bash
cd backend   && uv run uvicorn mdia.main:app --port 8000
cd frontend  && npm run dev
```

### 4. Settings first — the point of the screen

Nothing on Today means anything until the business goals are in, so open **Settings** and enter
NovaWear's:

| Field | Value |
|---|---|
| Gross margin | 55 % |
| Target CPA | ₹500 |
| Target ROAS | 3.5× |
| Monthly revenue goal | ₹80,00,000 |
| Monthly budget — Google Ads | ₹6,20,000 |
| Monthly budget — Meta Ads | ₹8,00,000 |
| Festive window | Diwali, 10–14 Nov 2026 |

Say the line while saving: break-even ROAS is **1.82×** — computed from the margin, never typed in.
Everything downstream is judged against these numbers.

---

## The demo

### Act 1 — six months of history (`/data` → `/`)

Drop `output/backfill/`'s four CSVs on the **Data** page. Each file shows the source it was
recognised as, from its headers; rejected rows would be listed per row, with the rest loaded.

Move to **Today**. It shows the as-of date, the KPI strip (Revenue, Spend, ROAS, MER, CPA) with
week-on-week deltas against the goal markers, and the 30-day trend. While the background analysis
runs the page says so; when it finishes, "Needs attention" fills in.

Point at the **pacing card**: Meta Ads is projected past its October budget (`demo_06`). Nobody
asked a question to get that — it is the difference between the run rate and the budget, in code.

### Act 2 — the week of 15 October, and *why* (`/opportunities`)

Upload `output/batch_2026-10-15/`. Today re-analyses and the list grows.

Open the Performance Max headroom (`demo_05`) or the fatiguing Instagram creative (`demo_07`) and
walk down the detail page in its own order:

1. **What happened** — the metric, the movement, the window, the rupee impact.
2. **Evidence** — the decomposition as an indented tree: CPA moved because CPC moved because CPM
   moved. Every number here is computed; the shares sum to 100 %.
3. **Likely cause** — the AI block, marked **grounded ✓**. The LLM ranked and phrased the
   hypotheses; each ID and number in its text was checked against the evidence above before it was
   allowed on screen. If it had invented one, the page would show the rule-based diagnosis instead
   and say so.
4. **Recommendation** — an action from the catalogue with its parameters, a confidence, a risk and a
   stop condition. The confidence is a formula, not an opinion — it drops when the data behind it is
   shaky.

Dismissing asks for a reason, because a dismissal is also a decision worth logging.

### Act 3 — the week of 22 October: don't touch anything yet (`/` → `/experiments`)

Upload `output/batch_2026-10-22/`. Meta's tracking breaks on the 24th (`demo_08`).

Today leads with the **trust banner**: Meta's platform conversions have fallen away from the store
orders they historically track, so that source reads *broken*. The consequence is the interesting
part — Meta's performance signals are **suppressed**, and its KPI numbers are greyed out. The system
would rather say "I don't trust this week's Meta data" than recommend a budget cut on a measurement
artefact.

What it does recommend is to fix the tracking. Take that recommendation, click **Create
experiment**, and approve it on the Experiments page: a 7-day test with a primary metric, a
baseline, a target and a stop condition, all filled in from the opportunity. Approving writes a
row in the decision log.

### Act 4 — the week of 29 October: the loop closes (`/experiments` → `/decisions` → `/reports`)

Upload `output/batch_2026-10-29/`. The tracking break has ended; the due experiment is evaluated
against the fresh week automatically.

- **Experiments** — the test moves to Completed with a verdict. In rehearsal: `fix_tracking` on
  `platform_conversions`, 28 Oct → 4 Nov, 33.4 before → 63.7 after, seven days of sample →
  **Worked ✓**. The verdict is a before/after test with a minimum-sample guard, so a two-day fluke
  reads *inconclusive* rather than *worked*.
- **Decisions** — the timeline shows the whole chain: the opportunity that raised it, the
  experiment that tested it, the outcome that settled it. This is the artefact a marketing team
  keeps; a dashboard has nothing like it.
- **Reports** — click **Generate**. The latest complete week is already selected. A founder summary
  on top, team detail below, copy as Markdown, print styles. The narrative is written by the LLM
  from the computed payload and passes the same grounding check; if it fails, the templated version
  goes out with the same numbers. In rehearsal it came back LLM-written and grounded ✓, opening on
  "Strong week: revenue was ₹27.61 L in the 7 days to 04 Nov 2026, rose 68% on the week before."

Close on the shape of it: CSVs in, a logged decision out, and every number on the way traceable to
code.

---

## If the LLM is down

It does not stop the demo, and that is worth showing deliberately. Point `LLM_MODEL` at a model id
that does not exist, restart the backend, and run an upload: the analysis still finishes, the
opportunity still has a diagnosis and a recommendation, the report still generates — each labelled
rule-based, with the AI block saying no AI wording was used. Restore `.env` afterwards.

## If something goes wrong on the day

| Symptom | What to do |
|---|---|
| Today is empty | Settings first, then the backfill upload — the empty state links to both |
| Today keeps saying it is analysing | The analysis runs in the background after each upload; the first run on an empty database is the slow one, as the top five opportunities are investigated one after another |
| An upload reports rejected rows | Expected only for deliberately malformed files; the valid rows still load |
| Numbers look greyed out in Act 1 or 2 | A source is failing a trust check — check the Data page badges; in Act 3 that is the story, earlier it is not |
| A screen shows an error card | Retry on the card; failures from writes appear as a toast with the API's own message |
| The report says no decisions were recorded | It counts decisions by when they were made, and the seeded data sits in the future — a decision taken during the demo is not inside the data's week. Show the chain on the Decisions page instead |

## How long each step takes

Measured on the rehearsal run: a clean clone against the Neon `test` branch, Bedrock as the
provider. Nothing here is fast enough to fill silence with, so talk over it — the waits are where
the trust and deterministic-first lines go.

| Step | Time |
|---|---|
| `uv sync` + `npm install` on a clean clone | ~2 min |
| Backfill upload (180 days, four files) | ~45 s |
| First analysis on an empty database | ~50 s |
| Each weekly upload | ~5 s |
| Each weekly analysis | ~50 s |
| Weekly report | ~10 s |

## Rehearsing

Run it end to end from a clean clone the day before — fresh `uv sync` and `npm install`, a wiped
database, the four uploads, timed. The generator is seeded, so what you see in the rehearsal is
what the room sees.

The rehearsal for this build found four things worth knowing:

- A clean clone needs the dev tools from `[dependency-groups]`, which `uv sync` installs by
  default; they used to sit in an extra that it skipped, so lint and tests failed on a fresh
  machine.
- Run durations on the Data page were reading under a second for runs that took the best part of a
  minute, because the finish time came from `now()` — the transaction's start.
- A tracking-fix experiment stated its levels as conversion counts ("from 0 to 1") when the
  tracking signal measures a share of normal; it now reads "from 20% of their usual level".
- Rupee amounts that look like `â‚¹` in a terminal are the console reading UTF-8 as
  Windows-1252, not bad data. Redirect to a file and open it as UTF-8 before believing it.
