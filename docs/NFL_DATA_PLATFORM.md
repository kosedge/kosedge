# NFL Data Platform (Enterprise Foundation)

This service is the dedicated ingestion layer for NFL data used by all downstream models.

## Why this exists

- Isolates ingestion runtime/tooling from model-serving runtime.
- Supports Python ecosystem packages that require newer runtimes (like `nflreadpy`).
- Makes data contracts explicit and reusable across multiple model versions.

## Service

- Path: `services/data-platform-nfl`
- Runtime: Python 3.11+
- Primary source: `nflreadpy` (nflverse)

## Database contract

Migration:

- `infra/db/012_nfl_data_platform.sql`

Tables:

- `nfl_dp_ingestion_runs` - run metadata, status, metrics, errors
- `nfl_dp_raw_objects` - canonical raw source objects with checksums
- `nfl_dp_schedules` - normalized schedule/results rows
- `nfl_dp_team_game_stats` - normalized team game stats
- `nfl_dp_player_game_stats` - normalized player game stats
- `nfl_dp_injuries` - normalized injury data
- `nfl_dp_rosters` - normalized roster data
- `nfl_dp_play_by_play` - normalized play-by-play rows from raw nflverse payloads
- `nfl_dp_player_usage_weekly` - weekly player usage features from normalized PBP
- `nfl_dp_team_situational_weekly` - weekly team situational features from normalized PBP
- `nfl_dp_team_rolling_features_weekly` - recency-weighted 3-game and 5-game team form features
- `nfl_dp_matchup_features_weekly` - per-game matchup feature pack for home vs away context
- `nfl_dp_team_features_latest` (view) - latest per-team feature snapshot

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

Direct service command:

- `cd services/data-platform-nfl`
- `PYTHONPATH=./src python3 -m data_platform_nfl.cli --seasons 2023,2024,2025,2026`

## Environment

Required:

- `DATABASE_URL`

Recommended:

- Run in a separate worker/deployment from model-service.
- Set source-specific quotas/limits in orchestration (future enhancement).

## Enterprise operations checklist

- Track `nfl_dp_ingestion_runs.status` and alert on `failed`.
- Monitor row deltas by table after each run.
- Backfill historical seasons in batches.
- Use checksums in `nfl_dp_raw_objects` for idempotency/audit.

## Paid data (optional upgrade path)

When you want to move beyond free-source latency/coverage:

- low-latency injury/practice feed
- market microstructure/limits feed
- tracking/advanced play event data

Integrate paid feeds into `nfl_dp_raw_objects` with new `source` values and keep normalized tables stable.
