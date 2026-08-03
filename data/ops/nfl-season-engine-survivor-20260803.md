# NFL Season Engine v1.4 — Survivor Pool Outputs

**Date:** 2026-08-03  
**Engine version:** `nfl-season-engine-v1.4-survivor`  
**Branch:** `feat/nfl-season-engine-survivor` → `deploy-vercel`  
**Package:** `services/model-service/src/services/nfl_season_engine/survivor.py`

## Goal

Make the hierarchical season engine useful for survivor pool decisions without breaking box scores, injury shocks, or usage layers.

## What shipped

1. **Season path simulation (team W/L)** — N full-season paths using Layers 1–2 (+ injury *strength* shocks). Layers 3–4 player boxes are skipped for throughput.
2. **Future week evaluation** — For any week N, rank teams by week win rate / pick-now score; report how often each team wins that week across sims.
3. **Path strength / future value** — Inspectable `save_score` + `pick_now_score` (not black-box EV).
4. **Already-used filter** — Recommendations exclude teams the user has already picked.
5. **API / CLI**
   - `POST /nfl/season-engine/survivor`
   - `GET /nfl/season-engine/status` exposes `survivor` capability + formula notes
   - `scripts/nfl/run_survivor_evaluate.py`
   - `scripts/nfl/run_hierarchical_season_sim.py --survivor-week N --already-used KC,BUF`

## Path-value formulas (documented)

Let `p[t,w]` = wins in week `w` for team `t` / `n_sims`.

```
save_score = 0.50 * future_avg_wp
           + 0.35 * future_max_wp
           + 0.15 * min(1.0, premium_spots / 3)

pick_now_score = this_week_wp
               - 0.45 * save_score
               + 0.10 * (this_week_wp - future_avg_wp)
```

- `future_*` = weeks **after** the evaluation week where the team is scheduled
- `premium_spots` = count of future weeks with `p[t,w] >= 0.70`
- Framing: high this-week WP + low unique future value → pick now; high `save_score` → lean save

## Example — Week 5, already used KC + BUF

Demo universe, `n_sims=400`, `seed=42`.

Artifact: `data/ops/nfl-survivor-example-20260803/survivor_evaluate.json`

| Rank | Team | Opp | H/A | Week WP | save_score | pick_now |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ARI | CAR | home | 0.645 | 0.424 | 0.478 |
| 2 | DEN | TEN | home | 0.683 | 0.564 | 0.444 |
| 3 | LV | NE | home | 0.558 | 0.383 | 0.401 |
| 4 | PIT | IND | away | 0.603 | 0.484 | 0.392 |
| 5 | LAC | NO | home | 0.648 | 0.594 | 0.390 |
| 6 | LA | NYG | home | 0.605 | 0.549 | 0.368 |
| 7 | PHI | JAX | away | 0.620 | 0.627 | 0.339 |
| 8 | DET | TB | home | 0.630 | 0.653 | 0.338 |

Notes from this run:

- **KC** (WP ≈ 0.67) and **BUF** (WP ≈ 0.61) are excluded from ranked picks as already used.
- **DET / PHI** have strong this-week WPs but higher `save_score` (easier later spots on the demo schedule), so they rank below softer one-week spots like ARI/DEN on `pick_now_score`.
- Demo schedule is placeholder round-robin — use DB schedule for production decisions.

### How often does Team Y win Week N?

From the same response `all_teams_week` (or `week_win_rate_for_team`):

- KC Week 5 WP ≈ **0.673** (unconditional; excluded from recommendations)
- DET Week 5 WP ≈ **0.630**
- PHI Week 5 WP ≈ **0.620**

## API shape

```bash
curl -sS -X POST "$MODEL_SERVICE/nfl/season-engine/survivor" \
  -H 'content-type: application/json' \
  -d '{
    "season": 2026,
    "week": 5,
    "n_sims": 500,
    "already_used": ["KC", "BUF"],
    "injury_paths": [],
    "seed": 42,
    "demo": true
  }'
```

Response includes `ranked_picks`, `all_teams_week`, `formula`, `diagnostics`, `engine_version`.

## Limitations (v1)

- Heuristic save / pick-now scores — **not** full multi-entry survivor EV or field correlation
- Demo schedule is round-robin; real `nfl_dp_schedules` preferred in DB mode
- Survivor paths skip player boxes (intentional); injury paths affect **strength** only in this mode
- HTTP default `n_sims=300` (cap 2000); heavier runs via CLI
- No web UI / Edge Board changes

## Tests

`services/model-service/tests/test_nfl_season_engine_survivor.py`

- already_used excluded
- week rankings ordered by win rate
- future_value higher for easier later spots (constructed matrix)
- injury_paths accepted without breaking
