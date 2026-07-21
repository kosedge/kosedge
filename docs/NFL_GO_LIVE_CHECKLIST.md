# NFL go-live checklist (seamless prod)

## Done

- [x] Web builds/deploys on Vercel (`apps/web`, Next.js)
- [x] Production branch set to `deploy-vercel` (pushes auto-promote)
- [x] Site live at https://www.kosedge.com

## Blockers (need credentials / Railway)

### 1) Vercel production env (currently only `ODDS_API_KEY`)

Add these in Vercel → Project → Settings → Environment Variables → Production:

| Variable | Value |
|---|---|
| `MODEL_SERVICE_URL` | Public Railway API URL, e.g. `https://<service>.up.railway.app` |
| `DATABASE_URL` | **Production** Postgres (not localhost) |
| `AUTH_SECRET` | Same secret used for NextAuth (≥32 chars) |
| `AUTH_URL` | `https://www.kosedge.com` |
| `INTERNAL_API_SECRET` | Shared secret with model-service (≥16 chars) |
| `ODDS_API_KEY` | Already set |

Redeploy after adding.

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
# apply SQL migrations including 037_nfl_data_resilience.sql
psql "$PROD_DATABASE_URL" -f infra/db/037_nfl_data_resilience.sql
# then ingest / restore owned NFL data (or restore the verified local dump)
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
