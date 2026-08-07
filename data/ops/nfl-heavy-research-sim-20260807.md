# NFL heavy research sims — launch current (2026-08-07)

## Status: COMPLETE

| Item | Value |
|------|-------|
| Engine | `nfl-season-engine-v1.12-survivor-planner-ux` |
| Team W/L paths | **100,000** (2616.5s / ~43.6 min) |
| Full player paths | **1,000** (1576.8s / ~26.3 min; 383 players) |
| Survivor | Week 1 eval derived from 100k team W/L paths |
| Seed | `20260807` |
| Finished | ~2026-08-07 14:35 ET (`EXIT:0`) |

## Output locations

**Repo ops bundle**

`data/ops/nfl-season-engine-launch-nfl-season-engine-v1.12-survivor-planner-ux-Nteam100000-Nplayer1000-20260807T172531Z/`

- `team_win_distributions.json`
- `team_week_win_rates.json`
- `player_season_totals.json`
- `survivor_week1_evaluate.json`
- `team_wins_from_player_paths.json`
- `run_summary.json`
- `LAUNCH_RESEARCH_NOTE.md`

**HD warehouse mirror**

`/Volumes/KosEdgeData/clean/nfl/research/nfl-season-engine-launch-nfl-season-engine-v1.12-survivor-planner-ux-Nteam100000-Nplayer1000-20260807T172531Z`

**Pointer**

`data/ops/nfl-launch-research-sims-current.md`

## Launch-current numbers (team W/L expected wins, top 10)

DET 11.31 · PHI 11.23 · SF 10.99 · KC 10.87 · BAL 10.64 · BUF 10.24 · HOU 10.01 · CIN 9.99 · GB 9.37 · MIN 9.13

## Honesty

- Packaged 2026 wall-chart schedule + nflverse depth — **preseason / research** labeling applies for guest-facing use.
- Heavy run was offline CLI; does **not** block live fantasy/survivor/game-box request paths.
- Bulk odds remain HD-first; this bundle is season-engine research only.
