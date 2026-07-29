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

## Pilot status (2026-07-29)

| Check | Result |
| --- | --- |
| Env wiring | **Done** (`NFL_SEASON_SIMS`) |
| Existing 50k bundle | Present under `data/ops/nfl-preseason-sim-2026-*` (if prior run) |
| Fresh 100k run this session | **Not completed** — full 100k is multi-hour (pairwise matrix + 100k replicates + player totals). Do not fake readiness. |

## Blockers / needs

1. Long wall-clock on local or Railway worker (prefer overnight).
2. Stable `DATABASE_URL` with 2026 market projections for all 272 REG games.
3. After run: verify `quality_checks.json` SB/division/playoff sums ≈ 1.0 / 8.0 / ~12–14.

## Honest readiness

Futures / win-total boards are **usable on existing ~50k bundle**; **100k is the production target**, not a blocker for selective Week-1 sides PLAY.
