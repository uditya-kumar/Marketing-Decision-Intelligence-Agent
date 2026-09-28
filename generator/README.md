# novawear-sim

Synthetic marketing data for **NovaWear**, a fictional Indian D2C ethnic-wear brand. It writes
platform-shaped CSV exports plus a `ground_truth.json` that labels every injected scenario.
Only `evaluation/` may read the ground truth; the backend never does.

```bash
uv sync
uv run novawear-sim backfill --days 180 --seed 42                  # history ending 2026-10-14
uv run novawear-sim batch --from 2026-10-15 --days 7               # next week, continues the backfill
uv run novawear-sim backfill --days 365 --schedule evaluation --out output/evaluation
uv run python scripts/plot_fatigue.py                              # CTR decay plot -> output/fatigue.png
uv run pytest
```

Options: `--seed`, `--schedule demo|evaluation|none`, `--out`, `--world PATH`, `--scenarios PATH`,
and `--end` for `backfill`.

## Output (per window)

| File | Shaped like | Grain |
|---|---|---|
| `google_ads.csv` | Google Ads ad report | day × ad × age × device |
| `meta_ads.csv` | Meta Ads Manager export (Facebook + Instagram) | day × ad × age × device |
| `web_analytics.csv` | GA4 exploration | day × source / medium × device |
| `store_orders.csv` | Shopify "Sales over time" | day |
| `ground_truth.json` | — | scenarios overlapping the window |

The numbers disagree the way real ones do:
- Store orders are the truth.
- GA4 records about 91% of them.
- Ad platforms over-claim by each channel's `attribution_ratio`. Google's data-driven attribution reports fractional conversions.

## How the world works

- `config/world.yaml` holds the hidden truth: channels, campaigns, ad sets, creatives and budgets, plus segments, the festive calendar, funnel rates, fatigue and Hill saturation.
- `config/scenarios.yaml` holds the named schedules:
  - `demo` is the dashboard storyline.
  - `evaluation` has ~50 labelled events, including no-issue windows.
- Every run simulates from the epoch (2025-09-01) using one random stream per (seed, stream, day). That makes a batch identical to the same slice of a longer backfill, and it means a scenario run differs from its counterfactual only where the scenario acts.
- Scenarios (`scenarios/`) only edit multiplicative modifiers before the simulation runs. Effects such as CTR decay under fatigue come out of the world model; they are not painted on.
