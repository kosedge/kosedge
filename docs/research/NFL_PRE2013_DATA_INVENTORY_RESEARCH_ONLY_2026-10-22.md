# Pre-2013 NFL data inventory (research only)

**Filed:** 2026-10-22  
**Eligibility:** **none claimed.** This is not a rebuild universe, not a cert set, and not ruling A (c).

C-7: the hist tree check **refuses** pre-2013 unless Ryan files `docs/research/NFL_RYAN_FILED_PRE2013_SEASONS.md`. That file is **not** present.

| Source (in-repo mention) | Provenance | Availability asserted here | Used by 3562/2992 scripts? |
| ------------------------ | ---------- | -------------------------- | -------------------------- |
| nflverse / nflreadpy PBP & schedules | Public GitHub; ingest starts at `START_SEASON = 2013` in `historical_market_backtest.py` | Whether older seasons exist in a private warehouse: **UNKNOWN** (no live query) | No |
| nflverse closing `spread_line` / `total_line` | Same | Pre-2013 coverage **UNKNOWN** | No |
| Owned Odds lake | `nfl_warehouse`; densify notes start 2020 | Pre-2013 owned OC: **thin / UNKNOWN** | No |
| The Odds API historical | Docs cite history often from **~2020** (`HISTORICAL_ODDS_CREDITS_ESTIMATE.md`) | Pre-2013 Odds history **likely absent**; not fetched | No |
| Packaged 2026 EPA / depth packs | 2019–2026 artifacts in repo | Pre-2013 packs **not found** in those paths | No |

No download was performed. No season is added to a diagnostic fold by this note.
