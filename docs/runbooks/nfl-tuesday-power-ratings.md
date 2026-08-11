# NFL Power Ratings Desk — Tuesday publish runbook

**Cutoff:** Tuesday **06:00 US/Eastern** after the prior week’s games are
final. If MNF/TNF makeup slides finals past that hour, wait until scores are
official, then run.

**Script:** `scripts/nfl/tuesday_power_ratings_update.py`  
**Wrapper:** `scripts/nfl/run-tuesday-power-ratings-update.sh`  
**α schedule:** `services/model-service/src/services/nfl_season_engine/power_ratings_desk.py` (`ALPHA_BY_WEEK`)

## Preseason

```bash
# Initial Model PR snapshot (no shrinkage) — safe any day
./scripts/nfl/run-tuesday-power-ratings-update.sh
# or
WEEK=0 ./scripts/nfl/run-tuesday-power-ratings-update.sh
```

Writes:

- `data/ops/nfl-power-ratings-desk/latest.json`
- `data/ops/nfl-power-ratings-desk/ryan_adj.json` (all adj = 0)
- `data/ops/nfl-power-ratings-desk/pointer.json`
- Tuesday audit + week snapshot JSON

## In-season (after week W finals)

```bash
WEEK=1 ./scripts/nfl/run-tuesday-power-ratings-update.sh
WEEK=1 ./scripts/nfl/run-tuesday-power-ratings-update.sh --dry-run
```

Per team audit fields: prior Model PR, PR_data, α, published Model PR,
Ryan Adj, Ryan PR, Off/Def/ST, week, `active_run_id`, timestamp.

## Ryan Adj

Edit `data/ops/nfl-power-ratings-desk/ryan_adj.json` only. Defaults are **0**.
Adj > 1.0 requires a non-empty `reason`. Never overwrite Model PR.

## Coherence

Same packaged strength path / `active_run_id` as Season Model wins & True PR.
Edge Board Model → KEI → tag is **not** modified by this job.
