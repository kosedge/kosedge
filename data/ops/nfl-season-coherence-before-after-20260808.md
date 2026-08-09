# NFL Season Coherence — Before / After (Phase 1)

Date: 2026-08-08  
Engine: `nfl-season-engine-v1.16-season-coherence`

## Before (published board)

Source: `data/ops/nfl-preseason-sim-2026-20260808T011817Z/player_regular_season_totals.csv`  
(engine label on pointer: `nfl-season-engine-v1.12-survivor-planner-ux`)

| Metric | Value |
|--------|------:|
| QB1s ≥ 4000 | **32 / 32** |
| QB1s ≥ 4500 | 2 |
| QB1 median | 4258.7 |
| QB1 p10 | 4045.2 |
| QB1 p90 | 4486.9 |
| QB1 min / max | 4011.4 / 4575.4 |
| QB1 mean | 4269.3 |
| League pass yards (all players) | 145714.7 |
| League rush yards | 55667.0 |
| Team mean wins sum (run_summary) | 272.0002 |

**Verdict:** FAIL — distribution shape is fantasy garbage despite a finite-looking pool.

## After (demo universe, n_sims=20, seed=42)

Measured with `simulate_full_season(build_demo_universe(2026), …)` after v1.16.

| Metric | Value | Target |
|--------|------:|--------|
| QB1s ≥ 4000 | **9** | 4–14 |
| QB1s ≥ 4500 | 2 | ≤ 5 |
| QB1 median | 3544.4 | 3400–3900 |
| QB1 p10 | 2827.8 | ≤ 3400 |
| QB1 p90 | 4331.0 | ≥ 4000 |
| QB1 min / max | 2573.2 / 4732.5 | left tail + small elite tail |
| QB1 mean | 3557.1 | — |
| League pass yards (named) | 113828 | 110–132k |
| League rush yards (named) | 47791 | 45–66k |
| Team budget pass pool | 120000 | conserved |
| Team budget rush pool | 56000 | conserved |
| mean_wins_sum | 272.0 | ≈ 272 |

Top QB1s (sample): Mahomes 4733, MIA 4525, CIN 4498, Allen 4331, Goff 4329  
Bottom QB1s (sample): CAR 2878, PIT 2828, TEN 2760, NE 2698, CLE 2573

**Verdict:** PASS — not all 32 ≥4000; realistic median/tails; W/L zero-sum holds;
league pools conserved at the budget layer.

## What changed in code

- Per-team `home_pace_plays` / `away_pace_plays`
- Attempt share of pass plays (sacks)
- Amplified strength/coaching pass identity
- Offense-coupled YPA + team season budgets (`season_budgets.py`)
- Path-end budget enforce + fantasy CSV allocator (`team_volume_budgets.py`)
- Scoring bridge stub + distribution / win-sum tests

## Republish note

Production web pointer still references the v1.12 bundle until a new launch
research run is published via `scripts/nfl/run_launch_research_sims.py` +
`publish_launch_research_to_web.py`. Regen that bundle on v1.16 before
claiming the live board is fixed.
