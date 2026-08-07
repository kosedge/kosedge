# NFL guest freshness banner — DR-only false degradation (2026-08-07)

## Symptom

Guest NFL pages (`/pro/nfl`, edge-board, fair-lines) showed amber:

`Data freshness degraded · S2026 W1` with `dr_backup:stale_296h>192h`

Model `/health` + `/health/db` were ok; board probes were offseason-unenforced.

## Root cause

`GET /health/nfl-data-freshness` always enforces the `dr_backup` SLO (8d / 192h), including offseason. Last `nfl_data_ownership_backups` pg_dump row was **2026-07-26** (~12.3d old) after the Aug 6 Postgres disk-full outage interrupted weekly DR jobs. Product UI treated that ops signal as board-data degradation.

## Fix

1. **Web** — hide guest banner when blockers are ops-only (`dr_backup:*`).
2. **Model-service** — split product `status`/`blockers` from `ops_status`/`ops_blockers`; product_guidance follows board SLOs only; ops alerts still fire on DR lag.
3. **Ops** — re-run `POST /api/jobs/run-nfl-dr-backup` once volume headroom is safe (capacity work deferred to **Thu Aug 13**). Enqueued 2026-08-07; timestamp had not advanced yet (likely dump still failing / worker issue).

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/health/nfl-data-freshness | jq '{status,ops_status,blockers,ops_blockers}'
# Guest pages should not render "Data freshness degraded" for DR-only.
```
