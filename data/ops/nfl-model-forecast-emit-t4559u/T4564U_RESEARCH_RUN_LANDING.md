# t4564u research run landing (SOP 4a017f22)

**CERT_CANDIDATE=0.** Not under seals/. F2 / #641 tip `385767a2` untouched.

| Field | Value |
|-------|--------|
| run_id | `nfl-mfe-2026-w08-20261027T212104Z-f50f15a8` |
| dest (GitHub / CoS-fetchable) | `data/ops/nfl-model-forecast-emit-t4559u/research_runs/nfl-mfe-2026-w08-20261027T212104Z-f50f15a8/` |
| dest (this VM only; not shared ops box) | `/workspace/ops/nfl_enterprise_green_t4359u/research_runs/nfl-mfe-2026-w08-20261027T212104Z-f50f15a8/` |
| forecast_ts_utc | `2026-10-27T21:21:04Z` |
| n | 14 W8 games |
| code_tip_sha8 | `f50f15a8` |
| CAR@GB record sha8 | `a1cf9f9f` |
| MANIFEST sha8 | `c4537c52` |
| missing_inputs | depth_sot_week, injury_paths_current, current_weekly_depth_db, inseason_efficiency_current, n_replicates_below_honest_precision |
| peer | `bc-e1ed23ad` (W8 engine run; no artifacts on their box at emit time) |

These are packaged-engine research numbers with explicit missing-input flags, not a current-W8 CLEAR.
