# NFL go-live checklist (seamless prod)

## Done

- [x] Web builds/deploys on Vercel (`apps/web`, Next.js)
- [x] Production branch set to `deploy-vercel` (pushes auto-promote)
- [x] Site live at https://www.kosedge.com
- [x] Vercel Production env has `MODEL_SERVICE_URL`, `AUTH_*`, `INTERNAL_API_SECRET`, `ODDS_API_KEY`
- [x] Enterprise sharpening commit on `deploy-vercel` (`78ac2356`) + Vercel prod alias verified

## Remaining (Railway / warehouse)

### 1) Optional Vercel env

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Only if web routes need direct Postgres (most NFL boards use `MODEL_SERVICE_URL`) |

### 2) Railway model-service (api + worker + beat)

From `services/model-service`:

1. `railway login`
2. Create/link 3 services from the same repo/Dockerfile:
   - api → `railway.json`
   - worker → `railway.worker.json`
   - beat → `railway.beat.json`
3. Set env on all three: `DATABASE_URL`, `REDIS_URL`/`CELERY_BROKER_URL`, `ODDS_API_KEY`, `INTERNAL_API_SECRET`
4. Deploy; copy the api public URL into Vercel `MODEL_SERVICE_URL`

### 3) Production warehouse

On the **prod** Postgres:

```bash
# apply SQL migrations through 038 (snap GSIS bridge)
psql "$PROD_DATABASE_URL" -f infra/db/037_nfl_data_resilience.sql
psql "$PROD_DATABASE_URL" -f infra/db/038_nfl_snap_usage_bridge.sql
# then ingest / restore owned NFL data (or restore the verified local dump)
# redeploy Railway api + worker + beat so sharpening code is live
```

### 4) Ops durability

On Railway (or backup runner):

- `NFL_DR_REMOTE_URI=s3://...`
- `NFL_ALERT_WEBHOOK_URL=https://hooks...`
- Confirm Celery beat is running so Tuesday resilience + daily freshness fire

## Verify

1. https://www.kosedge.com/pro/nfl/props — no “MODEL_SERVICE_URL is not configured”
2. `$MODEL_SERVICE_URL/health` → ok
3. `$MODEL_SERVICE_URL/health/nfl-data-freshness` → ok/degraded with payload
4. Props board shows rows for 2025 W17
