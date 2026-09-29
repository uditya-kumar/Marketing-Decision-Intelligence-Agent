---
marp: true
paginate: true
---

<!--
Defence deck, ~15 minutes: 6 minutes of slides, 7 of live demo (docs/demo.md), the rest questions.
Render with Marp (`marp docs/slides.md --pdf`) or present the markdown as is.
Speaker notes are the HTML comments; numbers come from evaluation/output/scorecard.txt.
-->

# MDIA

## Marketing Decision Intelligence Agent

From weekly CSV exports to a decision you can defend.

<!-- One student, one semester. Everything on these slides runs; the demo is the proof. -->

---

## Monday morning, a growth marketer

Four exports open: Meta, Google, GA4, Shopify.

- ROAS is down 12 %. **Why?**
- Is it the creative, the audience, the landing page — or the pixel?
- Last month we cut Meta's budget. **Did that work?** Nobody remembers.

A dashboard answers *what happened*. The job is *what to do about it*.

<!-- The gap is not data. It is diagnosis, and a memory of what was tried. -->

---

## Why not paste the CSVs into a chatbot?

| | Chatbot | MDIA |
|---|---|---|
| Numbers | invented as often as computed | computed in code, always |
| Evidence | a paragraph | a decomposition you can audit |
| Trust | none — it can't tell a broken pixel from a bad week | a gate before any advice |
| Memory | the chat scrolls away | a decision log with outcomes |

MDIA is **not a chatbot**. There is no chat.

<!-- The LLM is in here — but only where language is the deliverable. -->

---

## The pipeline

```
CSV exports ─► trusted KPIs ─► goal-aware signals ─► evidence-backed diagnosis
            ─► recommendation ─► experiment ─► verdict ─► decision log ─► weekly report
```

Each arrow is a screen. Each screen shows its working.

---

## The design rule: deterministic first

| Code (`domain/`, pure functions) | LLM (`agents/`) |
|---|---|
| KPIs, MER, break-even ROAS, goal status | ranking and phrasing hypotheses |
| change detection, scoring, grouping | choosing an action from the catalogue |
| the evidence tree | alternative explanations |
| trust, pacing, suppression | the weekly narrative |
| confidence, guardrails, verdicts | |

**The LLM never produces a number shown to a user.**

<!-- 18 modules, ~2,900 lines, no DB / HTTP / LangChain imports, coverage gated at 80% and sitting at 97%. -->

---

## Trust is the gate, not a footnote

Meta's platform conversions per store order, last 3 days vs its own 28-day baseline:

- below 0.60 → **warning**, below 0.45 → **broken**
- a broken pixel falls to ~0.15 within three days; ordinary days — festive peaks and real problems
  included — stay above ~0.68

When a source is broken: performance signals for that channel are **suppressed**, ROAS and CPA are
greyed out, confidence drops, and the only advice is *fix the tracking*.

<!-- The most valuable thing the system says all week is "don't touch anything yet". -->

---

## From signal to opportunity

- Four detectors: rolling-baseline change, goal breach, funnel-step drop, segment divergence.
- Scored by `|Δ| × ₹ impact`, with a ₹5,000 floor — a 60 % swing on a campaign spending nothing
  stays quiet.
- Suppressed first: festive windows, broken channels.
- Grouped by entity and window into one opportunity with a stable key, so the same problem is not
  raised twice.

---

## Diagnosis: evidence, then language

The evidence tree is arithmetic, not opinion (shape of it; the real one is on screen in the demo):

```
ROAS ▼ 18%
└─ CVR ▼ 14%   (78% of the movement)
   └─ mobile CVR ▼ 31%
└─ CPC ▲ 5%    (22%)
```

`CPA = CPC / CVR`, `ROAS = CVR × AOV / CPC`, log-change attribution, contributions sum to 100 %.

The LLM's job: read that tree, rank the plausible causes, say them in a sentence a marketer would
use, and name the alternatives it rejected.

---

## The grounding guard

Every model answer is checked against the evidence it was given, and may contain only:

- **signal IDs** that exist,
- **actions** from the catalogue, with parameters that validate,
- **numbers** that are in the evidence — read as a person reads them, so `₹16.39 L` and `1639000`
  are the same number.

Fail → retry with the violations as feedback (≤ 2) → otherwise the rule-based diagnosis, **labelled
on screen**.

Measured: 11 % of attempts violated the guard, every retry recovered, **0 ungrounded numbers ever
shown**.

<!-- An LLM outage is a branch in the graph, not an exception. The analysis never blocks on the model. -->

---

## Recommendation → experiment → decision

- An action from a fixed catalogue, with parameters, a risk and a stop condition.
- Confidence is a formula: signal strength, agreement between signals, share of the movement
  explained, and data trust — not the model's self-assessment.
- Guardrail: a protected campaign is never handed a `pause_*`.
- Approving it creates a 7-day experiment with a primary metric, a baseline and a target.
- Next week's upload evaluates it: **worked / did not work / inconclusive**, with a minimum-sample
  guard so a two-day fluke is not a win.
- Every approval, rejection and dismissal lands in the decision log, with its outcome.

<!-- This loop is the thesis: a system that remembers what it advised and what happened. -->

---

## Architecture

```
api/routes → services/ → repositories/ | domain/ (pure) | agents/
```

- FastAPI + SQLAlchemy 2 + Neon Postgres; React 19 + Vite + TanStack Query, types generated from
  OpenAPI.
- Two LangGraph graphs, both the same shape:
  `build evidence → LLM → ground_check ⟲ ≤2 → finalize (confidence, guardrails, priority in code)`.
- Evaluation is a separate package — the **only** code allowed to read the generator's
  `ground_truth.json`. A unit test fails if the backend so much as mentions it.

---

## Evaluation — 330 replayed days, 41 labelled scenarios

| Criterion | Target | Measured | |
|---|---|---|---|
| Tracking breaks caught | ≥ 90 % | **100 %** | pass |
| Advice suppressed while broken | ≥ 90 % | **100 %** | pass |
| Ungrounded numbers shown | 0 | **0** | pass |
| Cause in the top three | ≥ 80 % | 71 % | fail |
| Detected within 3 days | ≥ 80 % | 51 % | fail |
| False alarms | < 10 % | 67 % | fail |

Detected at all: 76 %. Median time to detect: 2 days. LLM diagnosis beats the rules on top-3
(71 % vs 52 %); on top-1 they tie.

<!--
Be straight about the three failures. Detection is tuned sensitive, and precision is scored only
against injected events — an unlabelled but real movement in the simulated world counts against us.
Slow-onset scenarios (creative fatigue: 2/8 inside three days) are what the rolling baseline is
worst at, by construction: a gradual decline moves the baseline with it. Threshold tuning and a
fatigue-specific detector are the first things I would do next.
-->

---

## What I would not claim

- **No causality.** An experiment's verdict is before/after on one metric, not a controlled trial.
- **Synthetic data.** A seeded world with known answers — which is what makes evaluation possible,
  and also what limits it.
- **No platform connectors.** CSV in, by design; the ingestion layer is where an API would slot in.
- Out of scope on purpose: chat, a budget simulator, notifications.

---

## Demo

```
upload → Today → open an opportunity → create and approve an experiment
       → upload next week → verdict → weekly report
```

<!-- docs/demo.md is the runbook. Four seeded weeks: Meta over-pacing, a fatiguing creative,
Performance Max headroom, and the tracking break that stops all advice. -->
