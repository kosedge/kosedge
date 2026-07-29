# NFL 100k season sim — complete

- Status: **completed**
- Bundle: `data/ops/nfl-preseason-sim-2026-20260729T160818Z`
- Generated: `2026-07-29T16:12:46Z`
- `season_monte_carlo_iterations`: **100000** (in `quality_checks.json`)
- Sanity: SB sum **1.0000** · division **7.9996** · playoff **13.9999**
- Projections hub readable: **yes** (latest by name sort)
- Player `publish_ready`: **false** (honest — see why below)

## Why publish_ready is false (do not flip)

1. **Pass gate:** 7 dual full-volume QB rooms (CIN, CLE, NO, ATL, SF, MIN, WAS) — two+ QBs each carrying starter-scale pass yards.
2. **Skill gate:** top rusher 1307.5 < 1400; top receiver 1234.9 < 1300; only 1 WR ≥1200 (need 3).

Team win totals / SB / playoff probs from the 100k MC are usable. Player season totals remain research-grade until depth-chart allocation clears those gates.
