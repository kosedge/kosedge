# NFL QB Starter Volume Lock — Diagnosis & Result

Generated: 2026-07-29  
Bundle: `data/ops/nfl-preseason-sim-2026-20260729T160818Z`  
Team/futures MC: **unchanged** (100k). Player layer regenerated only.

## Root cause

Week-1 depth charts already named the correct starters (Burrow, Daniels, Purdy, …),
but `nfl_player_projection_baselines` still emitted near-starter weekly
`pass_yards_mean` for backups — so season sums produced dual full-volume rooms:

| Team | Inflated backup-ish | Starter (depth w1) |
| --- | --- | --- |
| CIN | Flacco 3845 | Burrow 2290 |
| WAS | Mariota 3088 | Daniels 2651 |
| ATL | Tagovailoa 3585 | Penix 2439 |
| CLE / NO / SF / MIN | similar dual ≥1800 | — |

`compute_qb_starter_shares` exists in the weekly engine but was not enforced at
season-total aggregation for the hub CSVs.

## Fix (leakage-safe)

In `data_platform_nfl/player_season_totals.py`:

1. Load week-1 `nfl_dp_depth_chart_weekly` depth_order + prior-season pass attempts.
2. `designate_qb_starter_shares` (mirrors engine winner-take-most 0.92 / 0.06 / 0.02).
3. `apply_qb_starter_volume_lock`: room `full_rate = max(pass_yards)`; starter gets
   full_rate; backups get `full_rate * (share / primary_share)`.
4. Playoff CSVs derived from locked regular rates (no second designation).

Regen: `scripts/nfl/regen_player_season_totals.py` (no 100k re-run).

## Post-lock quality (honest)

| Gate | Result |
| --- | --- |
| `dual_full_volume_qb_rooms_count` | **0** (was 7) |
| Pass `publish_ready` | **true** (Goff 4122.8, not bridge) |
| Skill `publish_ready_skill` | **false** at lock time — rush 1307.5 &lt; 1400; rec 1234.9 &lt; 1300; wr1200=1 |
| Overall `publish_ready` | **false** at lock time |

Skill floors cleared later via prior-anchor calibration — see
`data/ops/nfl-skill-prior-anchor-report.md`. Thresholds were **not** cut.
