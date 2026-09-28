# MDIA — UI & User Flows

Visual tokens (colour, type, spacing, radius, shadows, motion) come from `designSystem.md`, and **they override any visual detail here**. The layouts are in `designFile.pen` (open it with the pencil MCP). This doc defines structure, flows and behaviour.

---

## 1. Design Principles

1. **Answer first, detail on demand.** Every screen opens with the conclusion ("CPA is above your limit on Meta"). Charts and tables sit below it.
2. **One primary action per view.** Each screen or card has one filled button; everything else is secondary or ghost.
3. **Calm by default.** Neutral surfaces, generous whitespace. Colour only means status: positive, negative, warning, info.
4. **Numbers you can trust.** Every number shows its comparison (vs last period or vs goal). LLM-written text is visually distinct from computed facts.
5. **Plain language.** Write "Ads are being shown too often" before "frequency 4.7". Jargon goes in secondary text.
6. **Not a chatbot.** There is no chat in the core product.

---

## 2. Information Architecture

```
Sidebar
├── Today            ← home: what needs me now
├── Opportunities    ← all issues & wins → detail page
├── Experiments      ← awaiting approval · running · completed
├── Decisions        ← decision log
├── Reports          ← weekly report
│
├── Data             ← upload, sources, trust, run history
└── Settings         ← margin, targets, budgets, festive windows, protected campaigns

Top bar: page title · as-of date · Upload button
```

Max depth is **2 levels** (list → detail page).

---

## 3. Layout Shell

```
┌────────────┬───────────────────────────────────────────────────────────┐
│ ◉ NovaWear │  Today                         Data as of 14 Oct  [Upload]│
│            ├───────────────────────────────────────────────────────────┤
│ ○ Today    │                                                           │
│ ○ Opport.  │          content (max-width ~1120px, centred)             │
│ ○ Experim. │                                                           │
│ ○ Decisions│                                                           │
│ ○ Reports  │                                                           │
│            │                                                           │
│ ○ Data     │                                                           │
│ ○ Settings │                                                           │
└────────────┴───────────────────────────────────────────────────────────┘
```

- The sidebar shows badge counts on Opportunities (open) and Experiments (awaiting approval).
- The **as-of date** is always visible in the top bar, so users know how fresh the data is.
- The target is desktop only.

---

## 4. Core User Flows

### Flow A: First run
```
Today (empty state) → "Set your goals" → Settings → "Upload data" → Data
      → files detected ✓ → "Analysing…" → Today
```

### Flow B: Monday morning check
```
Today → [trust banner?] → Needs attention card → Review → Opportunity page
      → Create experiment / Dismiss (reason) → back to Today
```

### Flow C: Act on a recommendation
```
Opportunity → Create experiment → review the auto-filled form → Approve
      → Experiments: Running (day 0/7)
```

### Flow D: Close the loop (next week)
```
Upload the next batch → analysis runs → Today: "Experiment completed: Worked ✓"
      → Experiments / Decisions show the before → after
```

### Flow E: Friday report
```
Reports → Generate this week → Copy as Markdown / Print
```

---

## 5. Screens

### 5.1 Today (home)

```
NovaWear                                                  Data as of Tue, 14 Oct

┌ ⚠ Meta tracking looks broken since 12 Oct. Purchases −82 %, store orders normal.
│   Performance advice for Meta is paused until it's fixed.       [See details]
└──────────────────────────────────────────────────────────────────────────────

 Revenue        Spend         ROAS          MER           CPA
 ₹1.9L          ₹48K          3.9×          3.2×          ₹428
 ▲ 6% vs LW     ▲ 2%          target 3.5 ✓  ▲ 0.1         limit ₹500 ✓
 ───────── 30-day trend (selected KPI) ─────────

 Needs attention · 2
 ┌──────────────────────────────────────────────────────────────┐
 │ HIGH  Meta "Kurta Sale" costs more per sale                  │
 │ CPA ₹610, above your ₹500 limit. Likely: ads shown too often │
 │ Confidence ●●●●○  · 4 signals                                │
 │                                           [Review]  Dismiss  │
 └──────────────────────────────────────────────────────────────┘

 Opportunities · 1                         Budget this month
 ┌───────────────────────────────┐         ┌───────────────────────────────┐
 │ Google Search is converting   │         │ 62% spent · 45% of month      │
 │ below target CPA   [Review]   │         │ ▓▓▓▓▓▓▓▓░░░░  Over pace       │
 └───────────────────────────────┘         │ Suggested: ₹11K/day (now ₹16K)│
                                           └───────────────────────────────┘
 Experiments
 Creative rotation · Day 4/7 · 1 awaiting approval →
```

The order is fixed: **Trust → KPIs → Needs attention → Opportunities + Pacing → Experiments.**
- If nothing needs attention, show a calm "All clear. Nothing needs you today."
- While an analysis is running, show "Analysing new data…" and keep the previous numbers visible.

### 5.2 Opportunity (detail page)

```
← Meta "Kurta Sale" costs more per sale                      HIGH · ●●●●○

 WHAT HAPPENED (computed)
 CPA rose 45% (₹420 → ₹610) over 7 days while spend rose 18%.

 WHY: EVIDENCE (computed)
   CPA ▲45%
    ├─ CPC ▲4%   · 9% of change
    └─ CVR ▼28%  · 91% of change
         └─ CTR ▼31% ← Frequency 2.1 → 4.7

 LIKELY CAUSE (AI · grounded ✓)
 1. Creative fatigue: the same ad shown too often to the same people.
 Other possibilities: audience competition (less likely: CPC barely moved).

 RECOMMENDED
 Rotate in a new creative in the same audience.
 Expected: CPA ₹510–₹545 · Risk: new creative has no history
 Watch: CPA · Stop if CPA > ₹650
                                           [Create experiment]  Dismiss

 ▸ Charts  ▸ Signals (4)
```

- The sections always appear in this order: **What happened → Why → Likely cause → Recommended.**
- Computed and AI sections have distinct labels. The AI section shows "grounded ✓", or "Rule-based" when the fallback was used.
- The evidence tree is an indented list, not a graph canvas.
- Dismiss asks for a short reason, which goes to Decisions.

### 5.3 Opportunities (list)

A segmented control filters the list: **All · Issues · Wins · Dismissed**. Each row shows a priority dot, title, channel, ₹ impact, confidence and age, and clicking it opens the detail page.

### 5.4 Experiments

Tabs: **Awaiting approval · Running · Completed.**
- **Awaiting approval:** the auto-filled form (hypothesis, action, metric, baseline, target, duration) with Approve and Reject (reason).
- **Running:** a progress bar (day X/Y) and the metric so far vs the baseline.
- **Completed:** a verdict chip (Worked / Didn't work / Inconclusive) with before → after.

### 5.5 Decisions

A timeline grouped by month. Each entry shows the date, decision (approved / rejected / dismissed), reason and outcome chip, and links to its opportunity and experiment.

### 5.6 Reports

A week picker and a "Generate" button, above a document view: the founder summary (5 lines) on top and the team detail below. Actions are Copy as Markdown and Print. Past reports appear in a list.

### 5.7 Data

- An upload zone (drag-drop, multiple files); each file shows its detected source and accepted/rejected row counts.
- A sources table: source, date range, rows, trust badge.
- Run history, with rejected rows you can expand.
- A "Download CSV templates" link.

### 5.8 Settings

A single form with sections for Business & economics (shows the live "Break-even ROAS: 2.5×"), Targets, Monthly budgets, Festive windows and Protected campaigns. One Save button.

---

## 6. Components & Patterns

| Pattern | Use |
|---|---|
| **KpiCard** | Value, delta vs period, goal marker |
| **Delta** | ▲▼ + %, coloured by *goodness*, not direction (CPA ▲ is negative) |
| **ConfidenceMeter** | 5 dots, with % on hover |
| **TrustBadge** | ok / warning / broken |
| **PriorityDot** | high / medium / low |
| **AiBlock** | Labelled section for LLM text, with a grounded or rule-based marker |
| **EmptyState** | Icon + one sentence + one action |

Formatting: ₹ with Indian grouping (₹6,00,000 · ₹1.9L · ₹2.4Cr), percentages with at most one decimal, and dates like "Tue, 14 Oct".

---

## 7. States Checklist (every screen)

- [ ] **Empty:** say what will appear, with one action (e.g. "Upload data to see your first insights").
- [ ] **Loading:** skeletons that match the final layout.
- [ ] **Error:** a plain message + retry. An LLM failure shows the rule-based result, labelled as such.
- [ ] **Low trust:** the trust banner, with affected numbers muted.
- [ ] **All clear:** a calm positive message instead of empty lists.

---

## 8. Motion & Accessibility

- Motion is subtle, fast (150–250 ms) and ease-out; the exact values are in `designSystem.md`.
- WCAG AA contrast.
- Status is never shown by colour alone (always icon + text).
- Focus rings are visible.
- Charts have a one-line text summary.
