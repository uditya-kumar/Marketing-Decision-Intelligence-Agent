# MDIA — UI & User Flows

Visual tokens (colour, type, spacing, radius, shadows, motion) come from `designSystem.md`. **When it exists, it overrides any visual detail here.** This doc defines structure, flows, and behaviour.

---

## 1. Design Principles

1. **Answer first, detail on demand.** Every screen opens with the conclusion ("CPA is above your limit on Meta"); charts and tables sit one click below.
2. **One primary action per view.** One filled button per screen/card; everything else is secondary or ghost.
3. **Calm by default.** Neutral surfaces, generous whitespace, one type family. Colour only means status: positive, negative, warning, info.
4. **Numbers you can trust.** Every number shows its comparison (vs last period / vs goal) and links to its source. LLM-written text is visually distinct from computed facts.
5. **Progressive disclosure.** Card → side sheet → full page. Users never lose their place.
6. **Plain language.** "Ads are being shown too often" before "frequency 4.7". Jargon appears as secondary text.
7. **Keyboard friendly.** ⌘K palette, ⌘J analyst, `Esc` closes any sheet.
8. **Not a chatbot.** Chat is a side panel, never the homepage.

---

## 2. Information Architecture

```
Sidebar
├── Today            ← home: what needs me now
├── Opportunities    ← all issues & wins, filterable
├── Plan             ← simulator + budget planner
├── Experiments      ← awaiting approval · running · completed
├── Reports          ← weekly founder / team reports
├── Decisions        ← memory timeline, searchable
│
├── Data             ← uploads, sources, trust status
└── Settings         ← profile, goals, budgets, calendar, guardrails

Global:  ⌘K command palette · ⌘J Ask Analyst panel · as-of date · Upload button
```

Max depth: **2 levels** (list → detail). Detail views open as side sheets from Today; full pages from their own section.

---

## 3. Layout Shell

```
┌────────────┬───────────────────────────────────────────────────────────┐
│ ◉ NovaWear │  Today                         Data as of 14 Oct  [Upload]│
│            ├───────────────────────────────────────────────────────────┤
│ ○ Today    │                                                           │
│ ○ Opport.  │                    content (max-width ~1120px,            │
│ ○ Plan     │                    centred, generous padding)             │
│ ○ Experim. │                                                           │
│ ○ Reports  │                                                           │
│ ○ Decisions│                                                           │
│            │                                                           │
│ ○ Data     │                                                           │
│ ○ Settings │                                                  ┌──────┐ │
│            │                                                  │ Ask ⌘J│ │
│  ⌘K Search │                                                  └──────┘ │
└────────────┴───────────────────────────────────────────────────────────┘
```

- Sidebar: collapsible to icons; badge counts on Opportunities and Experiments (awaiting approval).
- Top bar: page title, **as-of date** (always visible, so users know how fresh the data is), Upload.
- Analyst: floating button → right-side panel (does not cover main content on wide screens).

---

## 4. Core User Flows

### Flow A — First-time setup (< 5 minutes)

```
Welcome → 1. Business → 2. Goals & budget → 3. Upload data → Analysing… → Today
```

| Step | Fields | Notes |
|---|---|---|
| 1. Business | Name, currency, timezone | Prefilled ₹ / IST |
| 2. Goals & budget | Gross margin %, target CPA, target ROAS, monthly budget per channel | Shows live "Break-even ROAS: 2.5×" as margin is typed |
| 3. Upload | Drag-drop multiple CSVs | Auto-detects source per file ("Meta Ads ✓"); shows missing sources |
| Analysing | Step list with ticks: Validating → Computing KPIs → Checking data → Finding signals → Investigating | Real pipeline progress |

Calendar and guardrails are optional; set later in Settings, with a gentle prompt on Today.

### Flow B — Monday morning check (daily, 2 minutes)

```
Today → read summary → [trust banner?] → Needs attention card → Review
      → Opportunity sheet → Create experiment / Dismiss → back to Today
```

### Flow C — "Why is ROAS down?" (founder asks)

```
Today KPI "ROAS ↓" → click → Opportunity sheet → Evidence tree
      → Copy link / Ask Analyst "explain simply"
```

### Flow D — Act on a recommendation

```
Recommendation card → Simulate (if budget action) → Create experiment
      → review auto-filled hypothesis/metric/target/duration → Approve
      → Experiments: Running (day 0/7)
```

### Flow E — Close the loop (next week)

```
Upload new CSVs → pipeline runs → Today: "Experiment completed — Worked ✓"
      → Experiment detail (before vs after) → saved to Decisions
```

### Flow F — Monthly / festive planning

```
Plan → set total budget + goal → "Suggest best split" → adjust sliders
      → compare current vs proposed → Save plan (updates budgets for pacing)
```

### Flow G — Friday report

```
Reports → Generate this week → toggle Founder / Team → Copy / Export
```

### Flow H — "Why did we pause that?"

```
⌘K "pause kurta" → Decision → full chain: signal → hypothesis → decision → outcome
```

---

## 5. Screens

### 5.1 Today (home)

```
Good morning, NovaWear                                   Data as of Tue, 14 Oct

┌ ⚠ Meta tracking looks broken since 12 Oct. Purchases −82 %, store orders normal.
│   Performance advice for Meta is paused until fixed.            [See details]
└──────────────────────────────────────────────────────────────────────────────

 Revenue        Spend         ROAS          MER           CPA
 ₹1.9L          ₹48K          3.9×          3.2×          ₹428
 ▲ 6% vs LW     ▲ 2%          target 3.5 ✓  ▲ 0.1         limit ₹500 ✓
 ───────── 30-day trend (selected KPI) ─────────

 Needs attention · 2
 ┌──────────────────────────────────────────────────────────────┐
 │ HIGH  Meta "Kurta Sale" costs more per sale                  │
 │ CPA ₹610 — above your ₹500 limit. Likely: ads shown too often│
 │ Confidence ●●●●○  · 4 signals                                │
 │                                           [Review]  Dismiss  │
 └──────────────────────────────────────────────────────────────┘

 Opportunities · 1                         Budget this month
 ┌───────────────────────────────┐         ┌───────────────────────────────┐
 │ Google Search can take ~₹8K   │         │ 62% spent · 45% of month      │
 │ more at similar CPA [Simulate]│         │ ▓▓▓▓▓▓▓▓░░░░  Over pace       │
 └───────────────────────────────┘         │ Suggested: ₹11K/day (now ₹16K)│
                                           └───────────────────────────────┘
 Experiments
 Creative rotation · Day 4/7 · CPA ₹590 → ₹512 so far
 1 awaiting approval  →
```

Order is fixed: **Trust → KPIs → Needs attention → Opportunities + Pacing → Experiments.** If nothing needs attention: a calm "All clear. Nothing needs you today." state.

### 5.2 Opportunity (side sheet from Today, full page from Opportunities)

```
← Meta "Kurta Sale" costs more per sale                      HIGH · ●●●●○

 WHAT HAPPENED (computed)
 CPA rose 45% (₹420 → ₹610) over 7 days while spend rose 18%.

 WHY — EVIDENCE (computed)
 [ Evidence tree ]
   CPA ▲45%
    ├─ CPC ▲4%   · 9% of change
    └─ CVR ▼28%  · 91% of change
         └─ CTR ▼31% ← Frequency 2.1 → 4.7

 LIKELY CAUSE (AI · grounded ✓)
 1. Creative fatigue: the same ad shown too often to the same people.
 Other possibilities: audience competition (less likely: CPC barely moved).

 RECOMMENDED
 Replace Creative A with Creative C in the same audience.
 Expected: CPA ₹510–₹545 · Risk: Creative C has limited history
 Watch: CPA after 5,000 impressions · Stop if CPA > ₹650
                                  [Create experiment]  Simulate  Dismiss

 SIMILAR PAST DECISIONS
 Aug · Creative rotation on "Denim" → Worked (CPA −12%)

 ▸ Charts  ▸ Raw signals (4)
```

- Sections always in this order: **What happened → Why → Likely cause → Recommended → History.**
- Computed sections and AI sections have distinct labels; AI sections show a "grounded ✓" marker.
- Dismiss asks for a short reason (feeds Decisions).

### 5.3 Opportunities (list)

Filters as segmented control: **All · Issues · Wins · Dismissed**. Rows: priority dot, title, channel, ₹ impact, confidence, age. Click → full page.

### 5.4 Plan

```
 Total monthly budget  [ ₹6,00,000 ]   Goal  [ ROAS ≥ 3.5 ]   [Suggest best split]

 Channel      Current     Proposed                 Projected CPA   ROAS
 Google       ₹2.4L       ───────●────  ₹2.9L      ₹360            4.1×
 Meta         ₹2.0L       ─────●──────  ₹1.8L      ₹470            3.2×
 Instagram    ₹1.0L       ───●────────  ₹0.8L      ₹590            2.4×
 Email        ₹0.6L       ──●─────────  ₹0.5L      ₹120            9.0×

 ┌ Current ──────────────┐  ┌ Proposed ─────────────┐
 │ 1,240 orders · 3.3×   │  │ 1,310 orders · 3.6×   │  +5.6% (range +2–9%)
 └───────────────────────┘  └───────────────────────┘
                                                   Reset   [Save as plan]
```

Saturation hint on each slider ("returns flatten above ₹2.6L"). Guardrail limits shown as slider bounds.

### 5.5 Experiments

Tabs: **Awaiting approval · Running · Completed.**
- Awaiting: auto-filled form (hypothesis, action, metric, baseline, target, duration), then Approve / Edit / Reject (reason).
- Running: progress bar (day X/Y), metric so far vs baseline, sparkline.
- Completed: verdict chip (Worked / Didn't work / Inconclusive) with before → after and a link to the decision.

### 5.6 Reports

Week picker, then **Founder | Team** toggle, then the document view (serif-free, print-friendly). Actions: Copy, Export Markdown, Print/PDF. Past reports in a left list.

### 5.7 Decisions

Search bar + timeline grouped by month. Each entry: date, action, who decided, outcome chip. Detail shows the full chain as a vertical stepper: Signal → Hypothesis → Recommendation → Decision → Outcome.

### 5.8 Data

- Upload zone (drag-drop, multiple files), each file shows the detected source and row counts.
- Sources table: source, last date, rows, trust status badge.
- Run history with expandable rejected rows.
- "Download CSV templates" link.

### 5.9 Settings

Single page with left sub-nav: Profile · Goals & economics · Budgets · Calendar · Guardrails. Autosave with a subtle "Saved" indicator.

### 5.10 Ask Analyst panel

- Right panel, 400px. Suggested prompts based on current page ("Explain this opportunity simply").
- Shows tool steps as small chips ("Queried Meta CPA · 7d"). Citations are clickable and open the sheet.
- Answers never replace UI: they link to it.

---

## 6. Components & Patterns

| Pattern | Use |
|---|---|
| **KpiCard** | Value, delta vs period, goal marker, sparkline on hover |
| **Delta** | ▲▼ + % and colour by *goodness*, not direction (CPA ▲ = negative) |
| **ConfidenceMeter** | 5 dots + % on hover; tooltip explains factors |
| **TrustBadge** | ok / warning / broken |
| **PriorityDot** | high / medium / low |
| **AiBlock** | Labelled section for LLM text with grounded marker |
| **Sheet** | Right side sheet for detail from lists/Today |
| **EmptyState** | Icon + one sentence + one action |
| **Stepper** | Pipeline progress, decision chains |

Formatting: ₹ with Indian grouping (₹6,00,000 · ₹1.9L · ₹2.4Cr), percentages with one decimal at most, dates like "Tue, 14 Oct".

---

## 7. States Checklist (every screen)

- [ ] **Empty:** explains what will appear + one action (e.g. "Upload data to see your first insights").
- [ ] **Loading:** skeletons matching final layout (no spinners on full pages).
- [ ] **Pipeline running:** inline progress; stale data still visible with "Updating…".
- [ ] **Error:** plain message + retry; LLM failure shows rule-based result, labelled.
- [ ] **Low trust:** trust banner and muted affected numbers.
- [ ] **All clear:** a positive, calm message instead of empty lists.

---

## 8. Motion & Feedback

Subtle, fast (150–250 ms), ease-out; sheets slide, cards fade. No bouncing, no confetti. Optimistic updates for dismiss/approve with undo toast. Exact values from `designSystem.md`.

---

## 9. Accessibility

WCAG AA contrast; status never by colour alone (icon + text); full keyboard navigation; visible focus rings; charts have text summaries.
