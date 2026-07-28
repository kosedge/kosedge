# NFL Data Resilience (Subscription Ops)

This runbook covers owned-data DR, weekly automation, source fallbacks, and freshness SLOs so Kos Edge can survive nflverse outages and still operate as a paid product.

## Goals

1. **Own the warehouse** — Postgres is source of truth for product boards.
2. **Recover from disk/host loss** — compressed `pg_dump` with verify + retention.
3. **Refresh every week** — automated Tuesday resilience cycle.
4. **Degrade honestly** — stale/missing sources surface in ops + Pro UI.
5. **Escape hatch** — licensed feed evaluation path when free sources fail SLOs.

## What is owned

| Domain            | Owned tables                                   | Primary               | Fallback              |
| ----------------- | ---------------------------------------------- | --------------------- | --------------------- |
| Schedules/scores  | `nfl_dp_schedules`                             | nflverse schedules    | ESPN scoreboard       |
| PBP               | `nfl_dp_raw_objects`, `nfl_dp_play_by_play`    | nflverse PBP          | none (licensed later) |
| Player/team stats | `nfl_dp_*_game_stats`                          | nflverse              | NFL.com team intel    |
| Injuries/rosters  | `nfl_dp_injuries`, `nfl_dp_rosters`            | nflverse / NFL.com    | each other            |
| Snaps             | `nfl_dp_snap_counts_weekly`                    | nflverse snap counts  | PBP proxy shares      |
| Depth             | `nfl_dp_official_depth_charts`, inferred depth | nflverse depth charts | inferred usage depth  |
| Props odds        | `nfl_player_prop_market_snapshots`             | The Odds API          | last owned snapshots  |

Executable matrix: `data_platform_nfl.source_matrix.source_matrix_payload()`.

## DR backup

```bash
./scripts/nfl/run-ownership-dr-backup.sh
```

Produces:

- `data/backups/nfl/kosedge-nfl-<UTC>.dump` (pg_dump custom, compress=9)
- `.sha256` sidecar
- row in `nfl_data_ownership_backups` (`backup_type=pg_dump`)
- restore verification into ephemeral `kosedge_dr_verify_*` DB (drop after)

Env:

| Var                     | Purpose                                            |
| ----------------------- | -------------------------------------------------- |
| `NFL_DR_BACKUP_DIR`     | Local dump directory (default `data/backups/nfl`)  |
| `NFL_DR_BACKUP_KEEP`    | Retention count (default `3`)                      |
| `NFL_DR_REMOTE_URI`     | Optional `s3://bucket/prefix` (requires AWS CLI)   |
| `NFL_PG_BIN_DIR`        | Directory containing `pg_dump`/`pg_restore`/`psql` |
| `NFL_ALERT_WEBHOOK_URL` | Slack/Discord/etc webhook for ops alerts           |

## Weekly automation

```bash
./scripts/nfl/run-weekly-resilience-cycle.sh
# or enqueue:
# POST /api/jobs/run-nfl-weekly-resilience-cycle
```

Celery Beat (when worker+beat are running):

- **Tue 04:15** — `run_nfl_weekly_resilience_cycle` (ingest → player update → DR → freshness)
- **Daily 08:10** — `run_nfl_data_freshness_check`
- **Sun 03:40** — extra `run_nfl_dr_backup`

## Freshness SLOs

- Health: `GET /health/nfl-data-freshness`
- Prometheus: `GET /health/nfl-data-freshness/prometheus`
- Pro UI: amber banner on `/pro/nfl/*` when status ≠ `ok`
- Snapshots: `nfl_data_freshness_snapshots`
- Alerts: `nfl_ops_alert_events` (+ webhook when configured)

In-season max ages (hours): injuries 24, schedules 36, PBP/stats/snaps 48, rosters/depth 72, props odds 6, DR backup 192 (8d).

## Licensed feed gate

Do **not** scrape as the primary production path for a paid product.

Buy SportsDataIO / Sportradar / Opta when:

1. nflverse becomes unavailable/paid beyond tolerance, or
2. subscribers require freshness SLOs free sources cannot meet.

Adapters must write `nfl_dp_raw_objects` with `source=<vendor>` then normalize into existing typed tables.

## Restore drill

```bash
pg_restore --clean --if-exists --no-owner --no-acl \
  -d postgresql://USER:PASS@HOST:5432/kosedge_restore \
  data/backups/nfl/kosedge-nfl-XXXX.dump
```

Confirm row counts for `nfl_dp_schedules`, `nfl_dp_play_by_play`, `nfl_dp_raw_objects`.
