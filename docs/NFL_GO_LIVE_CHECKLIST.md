# NFL go-live checklist (seamless prod)

## Done

- [x] Web builds/deploys on Vercel (`apps/web`, Next.js)
- [x] Production branch set to `deploy-vercel` (pushes auto-promote)
- [x] Site live at https://www.kosedge.com
- [x] Vercel Production env has `MODEL_SERVICE_URL`, `AUTH_*`, `INTERNAL_API_SECRET`, `ODDS_API_KEY`
- [x] Enterprise sharpening commit on `deploy-vercel` (`78ac2356`) + Vercel prod alias verified

## Remaining (Railway / warehouse)

### 1) Optional Vercel env

| Variable       | Notes                                                                             |
| -------------- | --------------------------------------------------------------------------------- |
| `DATABASE_URL` | Only if web routes need direct Postgres (most NFL boards use `MODEL_SERVICE_URL`) |

### 2) Railway model-service (api + worker + beat) — one-push

**Project:** `brave-art`  
**Services:** `model-service` (api), `model-service-worker`, `model-service-beat`  
**API URL:** `https://model-service-production-e253.up.railway.app`  
**Process roles:** `PROCESS_TYPE=api|worker|beat` on each service  
**Deploy shape:** `railway up services/model-service --path-as-root` (vendors `data_platform_nfl` in the image)

**Preferred:** GitHub Actions on `deploy-vercel` (`.github/workflows/deploy-railway.yml`).

One-time GitHub secret (Settings → Secrets and variables → Actions):

| Secret          | Value                                                         |
| --------------- | ------------------------------------------------------------- |
| `RAILWAY_TOKEN` | Railway → `brave-art` → Settings → Tokens → **Project Token** |

Optional overrides (defaults match brave-art): `RAILWAY_SERVICE_API`, `RAILWAY_SERVICE_WORKER`, `RAILWAY_SERVICE_BEAT`, `RAILWAY_ENVIRONMENT`.

After `RAILWAY_TOKEN` is set, any push to `deploy-vercel` that touches `services/model-service/**` deploys all three.

### 3) Production warehouse

On the **prod** Postgres (public URL or `railway ssh` into model-service), use the
tracked migration runner — not ad-hoc `psql` for new work. See `infra/db/README.md`.

**Current cutover (tracker only):** production already has hand-applied SQL through
`054` (nullable `nfl_player_prop_model_edges.confidence`, no default) with **no**
`schema_migrations` rows. Verified 2026-09-03. Do **not** re-apply 054.

```bash
# Explicit baseline through 054 (stamps only — never implicit). No apply.
DATABASE_URL="$PROD_DATABASE_URL" python scripts/db/migrate.py baseline --through 054
DATABASE_URL="$PROD_DATABASE_URL" python scripts/db/migrate.py status --require-current
# After stamp: apply is a no-op until a future 055+. Never replay 054.
```

Historical (pre-runner) note — these were applied once by hand / one-off scripts:

```bash
# historical: snap GSIS bridge era
# psql "$PROD_DATABASE_URL" -f infra/db/037_nfl_data_resilience.sql
# psql "$PROD_DATABASE_URL" -f infra/db/038_nfl_snap_usage_bridge.sql
# or: railway ssh -s model-service -- python scripts/nfl/apply_038_prod.py
```

Then ingest / restore owned NFL data (or restore the verified local dump) as needed.

Freshness is wired; current prod blocker is `dr_backup:missing_timestamp` (offseason degraded is expected until DR backup lands).

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
