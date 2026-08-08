# NFL launch research sims — 20260807T214449Z

- **Engine:** `nfl-season-engine-v1.12-survivor-planner-ux`
- **Preseason:** yes (honest launch research label)
- **Team W/L sims:** 50,000 (Layers 1–2; win distributions + week matrix)
- **Full player sims:** 1,000 (Layers 1–4 path-coherent)
- **Survivor artifact:** week 1 eval at n=50000
- **Universe:** packaged / schedule=packaged_wall_chart_2026 / roster=packaged_nflverse_depth_2026
- **Output dir:** `/Users/ryankos/kosedge/data/ops/nfl-season-engine-launch-nfl-season-engine-v1.12-survivor-planner-ux-Nteam50000-Nplayer1000-20260807T214449Z`
- **Timing:** team 72.5m · player 140.9m · survivor 0.0m
- **Sanity:** mean_wins_sum=272.0002 (expect ~272)

## Launch-current numbers

These season-engine artifacts are the **launch-current research** board for:
- season win distributions (`team_win_distributions.json`)
- week win-rate matrix for survivor path research (`team_week_win_rates.json`)
- player season projections (`player_season_totals.json`) when player sims ran
- W1 survivor ranking sample (`survivor_week1_evaluate.json`)

Separate hub futures board (market Bernoulli MC, 100k): `data/ops/nfl-preseason-sim-2026-20260729T160818Z` (`nfl-v1.5-matchup-sim`).

## Caps / honesty

- Full hierarchical player paths are ~10s/path; launch research capped player N at **1000** (not 50k).
- Team W/L paths reached **50000** (target band 50k–100k).
- Interactive UI / Railway HTTP remain capped (≤500) so desks stay responsive.
