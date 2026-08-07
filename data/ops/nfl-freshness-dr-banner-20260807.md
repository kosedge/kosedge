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
3. **Ops** — `POST /api/jobs/run-nfl-dr-backup?skip_verify=true` enqueued 2026-08-07; new `pg_dump` row landed at **2026-08-07T16:04:34Z** (`age_hours≈0.15`).

## Before / after (prod)

| Check | Before | After |
|-------|--------|-------|
| `/health/nfl-data-freshness` | `degraded`, blockers=`dr_backup:stale_296h>192h` | `status=ok`, `ops_blockers=[]`, DR age ~0.15h |
| `/pro/nfl`, edge-board, fair-lines | Amber “Data freshness degraded · S2026 W1” | No guest degraded banner |
| Ship | — | `deploy-vercel` @ `7957c067` (+ defense-in-depth code) |

## Verify

```bash
curl -sS https://model-service-production-e253.up.railway.app/health/nfl-data-freshness | jq '{status,ops_status,blockers,ops_blockers,dr:.checks.dr_backup}'
# Guest pages should not render "Data freshness degraded" for DR-only.
```
