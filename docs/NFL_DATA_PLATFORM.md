# NFL Data Platform (Enterprise Foundation)

This service is the dedicated ingestion layer for NFL data used by all downstream models.

## Why this exists

- Isolates ingestion runtime/tooling from model-serving runtime.
- Supports Python ecosystem packages that require newer runtimes (like `nflreadpy`).
- Makes data contracts explicit and reusable across multiple model versions.

## Service

- Path: `services/data-platform-nfl`
- Runtime: Python 3.11+
- Primary source priority:
  - `api.nfl.com` (NFL.com) for Team Intel rosters + team stats + standings
  - `nflreadpy` (nflverse) fallback when NFL.com fetch/auth/parse fails

## Database contract

Migration:

- `infra/db/012_nfl_data_platform.sql`
- `infra/db/022_nfl_team_intel.sql`
- `infra/db/023_nfl_team_situational_source.sql`
- `infra/db/025_nfl_launch_hardening.sql`
- `infra/db/029_nfl_rookie_draft_capital.sql`
- `infra/db/030_nfl_usage_weekly_source_tracking.sql`

Tables:

- `nfl_dp_ingestion_runs` - run metadata, status, metrics, errors
- `nfl_dp_raw_objects` - canonical raw source objects with checksums
- `nfl_dp_schedules` - normalized schedule/results rows
- `nfl_dp_team_game_stats` - normalized team game stats
- `nfl_dp_player_game_stats` - normalized player game stats
- `nfl_dp_injuries` - normalized injury data
- `nfl_dp_rosters` - normalized roster data, including `entry_year`/`rookie_year`/`draft_number` (sourced directly from nflreadpy's `load_rosters()`)
- `nfl_dp_play_by_play` - normalized play-by-play rows from raw nflverse payloads
- `nfl_dp_player_usage_weekly` - weekly player usage features from normalized PBP. `source` distinguishes real (`pbp_aggregation`) from synthetic preseason rows (`preseason_hydrate_v1`, `rookie_baseline_v1`) -- see "Preseason bootstrap" below
- `nfl_dp_team_situational_weekly` - weekly team situational features from normalized PBP
- `nfl_dp_team_situational_weekly.source` marks active source (`nfl_com` preferred, `nflverse` fallback, `preseason_hydrate_v1` for synthetic preseason rows)
- `nfl_dp_rookie_usage_baselines` - historical rookie-year usage baselines by `(position, draft_tier)`, recency-weighted, recomputed by `rookie_baselines.compute_rookie_usage_baselines()`
- `nfl_dp_team_rolling_features_weekly` - recency-weighted 3-game and 5-game team form features
- `nfl_dp_matchup_features_weekly` - per-game matchup feature pack for home vs away context
- `nfl_dp_standings_weekly` - derived weekly team standings from completed schedules
- `nfl_dp_depth_chart_weekly` - inferred weekly role hierarchy by team and position
- `nfl_dp_team_features_latest` (view) - latest per-team feature snapshot
- `nfl_data_ownership_backups` - immutable backup manifests for owned-data snapshots

## Run ingestion

From repo root:

- `pnpm ingest:nflverse`
- `pnpm ingest:nflverse:no-pbp` (faster, skips heavy PBP raw ingestion)
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2013,2014,2015 --normalize-pbp-from-raw`
- add `--replace-normalized` to rebuild normalized rows for those seasons from raw source
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2013,2014,2015 --materialize-usage-features`
- add `--replace-usage-features` to fully rebuild usage/situational features for those seasons
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2013,2014,2015 --materialize-matchup-features`
- add `--replace-matchup-features` to fully rebuild rolling/matchup features for those seasons
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2025,2026 --materialize-standings-weekly`
- add `--replace-standings-weekly` to rebuild derived standings rows for those seasons
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2025,2026 --materialize-depth-chart-weekly`
- add `--replace-depth-chart-weekly` to rebuild inferred depth-chart rows for those seasons
- all materializers support `--week` for deterministic week-scoped runs
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --run-launch-hardening --seasons 2025,2026`
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --backup-owned-data --seasons 2026 --backup-include-row-exports`

Direct service command:

- `cd services/data-platform-nfl`
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2023,2024,2025,2026`

## Environment

Required:

- `DATABASE_URL`

Recommended:

- Run in a separate worker/deployment from model-service.
- Set source-specific quotas/limits in orchestration (future enhancement).
- Configure NFL.com auth for preferred Team Intel ingestion:
  - `NFL_COM_BEARER_TOKEN` (preferred when available), or
  - `NFL_COM_CLIENT_ID`, `NFL_COM_CLIENT_KEY`, `NFL_COM_CLIENT_SECRET`, `NFL_COM_DEVICE_ID`
- Optional resiliency tuning:
  - `NFL_COM_TIMEOUT_SECONDS` (default `8.0`)
  - `NFL_COM_RETRIES` (default `2`)
  - `NFL_COM_USER_AGENT`

## NFL.com endpoints used

- `GET https://api.nfl.com/football/v2/rosters` (team rosters, normalized into `nfl_dp_rosters`)
- `GET https://api.nfl.com/football/v2/standings` (team standings, normalized into `nfl_dp_standings_weekly`)
- `GET https://api.nfl.com/football/v2/stats/team-stats` (team-level stats aggregates for Team Intel stats rows)
- `GET https://api.nfl.com/football/v2/weeks/date/{YYYY-MM-DD}` (resolve current week/season type)

## Enterprise operations checklist

- Track `nfl_dp_ingestion_runs.status` and alert on `failed`.
- Monitor row deltas by table after each run.
- Backfill historical seasons in batches.
- Use checksums in `nfl_dp_raw_objects` for idempotency/audit.
- Emit owned-data backup manifests (`nfl_data_ownership_backups`) each weekly cycle.
- Store export artifacts under `data/ops` for cold-path recovery.

## Free-source expansion (NFL)

- `api.nfl.com` (`/rosters`, `/standings`, `/stats/team-stats`) for team intel overlays.
- `ESPN scoreboard API` for game schedule context and fallback completed-game outcomes.
- `Open-Meteo` forecast API for weather context used in environment decomposition.
- `The Odds API` for market snapshots (NFL defaults to DraftKings unless overridden).

Reliability notes:

- NFL.com auth can rotate; keep `NFL_COM_BEARER_TOKEN` or client credentials current.
- ESPN scoreboard is a fallback for missing final scores, not primary market data.
- Open-Meteo is best-effort and should not hard-fail market sims.
- The Odds API free credits can run out during dense polling windows; monitor `x-requests-remaining` in odds task output.

## Year-to-year automation runbook

The following idempotent scripts are now available:

- `scripts/nfl/run-preseason-bootstrap.sh`
- `scripts/nfl/run-weekly-inseason-refresh.sh`
- `scripts/nfl/run-daily-market-sim-refresh.sh`
- `scripts/nfl/run-postweek-grading.sh`

Each script can be re-run safely and writes deterministic artifacts through DB upserts plus backup manifests.

## Preseason bootstrap (team + player priors, rookies)

`scripts/nfl/run-preseason-bootstrap.sh` should be the *only* thing anyone
ever needs to run at the start of a new season. It now includes a step that
used to be a one-off, uncommitted manual fix
(`scripts/nfl/fix_2026_preseason_priors.py`, since deleted) and is a real,
tested, idempotent module instead:
`services/data-platform-nfl/src/data_platform_nfl/preseason_hydration.py`.

Before any real games are played in a new season, `nfl_dp_team_situational_weekly`
and `nfl_dp_player_usage_weekly` have nothing to go on for that season. The
bootstrap seeds a real prior instead of leaving that gap or (the bug this
replaced) silently carrying forward a single noisy snapshot:

- **Team priors** (`hydrate_preseason_team_situational`): full *prior-season
  average* per team for every situational column, optionally blended 50/50
  with a Super Bowl-futures market percentile (`market_signals.py`, needs
  `ODDS_API_KEY`). A walk-forward backtest showed the full-season average
  beats a single-game/week snapshot by 47-62% lower MAE against real
  following-season outcomes, essentially unbiased (see
  `data/ops/nfl-preseason-methodology-backtest-report.md`).
- **Player priors** (`hydrate_preseason_player_usage`): every rostered
  player gets a real row, not just the ones who happened to record usage in
  the prior season's final week:
  - Returning players get their real full-prior-season per-game average,
    remapped to their **current** roster team (handles free agency/trades).
  - Rookies -- and anyone else with zero prior-season usage -- get a real
    historical baseline from `nfl_dp_rookie_usage_baselines`
    (`rookie_baselines.py`), bucketed by `(position, draft_tier)` from real
    rookie-season outcomes 2013-present, recency-weighted (`DEFAULT_RECENCY_DECAY`)
    to track drift like the shrinking rookie-RB workload trend. A walk-forward
    backtest against 2019-2024 draft classes cut MAE 58-61% vs. the previous
    status quo (rookies silently absent = implicitly projected at 0).
  - Only `SKILL_OFFENSE_POSITIONS` (QB/RB/WR/TE/FB/HB) get a real baseline --
    this usage table has no signal for OL/DL/LB/DB/ST, so those positions
    get an explicit all-zero baseline rather than borrowing another
    position's shape.
- Both writers are guarded to only ever touch rows tagged with their own
  synthetic `source` values -- they never overwrite a real, played week.
  Stale rows for players who changed teams or left the league entirely are
  cleaned up automatically.
- **After hydrating, the downstream feature tables must be rebuilt** --
  `--materialize-matchup-features --replace-matchup-features` and
  `--materialize-player-projection-features --replace-player-projection-features`
  -- since they're derived FROM the tables just hydrated. The bootstrap
  script does this automatically; if you call `run_preseason_bootstrap()`
  directly, remember this last step.

Run it standalone any time (safe to re-run):

```bash
cd services/data-platform-nfl
PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2025,2026 --run-preseason-bootstrap
# --prior-season to override, --no-market-signal to skip the Odds API call
```

Validation reports live in `data/ops/nfl-preseason-methodology-backtest-report.md`
and the analysis scripts that produced them in
`data/ops/nfl-preseason-methodology-backtest/`.

## Paid data (optional upgrade path)

When you want to move beyond free-source latency/coverage:

- low-latency injury/practice feed
- market microstructure/limits feed
- tracking/advanced play event data

Integrate paid feeds into `nfl_dp_raw_objects` with new `source` values and keep normalized tables stable.

## Current limitations (free data path)

- Conference/division metadata in `nfl_dp_standings_weekly` is nullable until a stable free alignment source is integrated.
- `player_uid` in `nfl_dp_depth_chart_weekly` is nullable in v1 and can be backfilled from the identity graph later.
- Depth roles are deterministic but inferred (`v1_usage_roster_injury`) from roster, recent usage, and injury status rather than official team depth publications.
