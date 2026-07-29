# NFL 100k Season Sims Path

## Command

```bash
export DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge
export NFL_SEASON_SIMS=100000
cd /Users/ryankos/kosedge
.venv/bin/python scripts/nfl/simulate_2026_season.py
```

Default without env is **50,000** replicates (`N_REPLICATES = int(os.getenv("NFL_SEASON_SIMS", "50000"))`).

## What it writes

`data/ops/nfl-preseason-sim-2026-<timestamp>/` including:

- `team_regular_season_outcomes.csv` (win totals / playoff / SB)
- `player_regular_season_totals.csv` / `player_playoff_totals.csv`
- `quality_checks.json` / `run_summary.json`

Web hub reads the latest bundle via `apps/web/lib/nfl-preseason-artifacts.ts`.

## Status (2026-07-29)

| Check | Result |
| --- | --- |
| Env wiring | **Done** (`NFL_SEASON_SIMS`) |
| Fresh 100k run | **Completed** → `data/ops/nfl-preseason-sim-2026-20260729T160818Z` |
| Iterations | **100000** (`quality_checks.json` metadata) |
| Sanity | SB 1.0000 · division 7.9996 · playoff 13.9999 |
| Player `publish_ready` | **false** (7 dual QB rooms; skill leader floors) — do not fake |

Progress: `data/ops/nfl-100k-sim-progress.{json,md}` · Log: `data/ops/nfl-100k-sim-run.log`

## Honest readiness

Team futures / win totals from the **100k** bundle are production-usable for the hub.  
Player season totals stay **research-grade** until depth-chart volume clears `publish_ready`.  
100k is **not** a blocker for selective Week-1 sides PLAY.
