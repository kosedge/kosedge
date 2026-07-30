# Railway season ops (brave-art)

## Mental model (critical)

| Cadence | What runs | What does **not** |
| --- | --- | --- |
| **Hourly 7:00–23:00 (current)** | Odds (:00) + context (:20) + light board sims (:15) | Container redeploy |
| **3:00am ET daily** | Full **data** refresh: odds → context → fuller sims → market history | Redeploying Vercel/web |
| **On code change** | One-button / CI `railway up --path-as-root` for api+worker+beat | — |
| **In-season (later)** | Tight windows around injury reports (e.g. */5–*/10) — env overrides only | Blind 24/7 spam |

Redeploying every few minutes is wrong. **Data refresh ≠ deploy.**  
“Reset the whole website at 3am” = refresh **boards/odds/projections data**, not rebuild the Next.js app.

## Services

| Service | `PROCESS_TYPE` | HTTP | Notes |
| --- | --- | --- | --- |
| `model-service` | **`api`** | `:8080` `/health` | Must NEVER be `beat` or `worker` |
| `model-service-worker` | `worker` | none | Uses `railway.worker.json` (no healthcheck) |
| `model-service-beat` | `beat` | none | Uses `railway.beat.json` (no healthcheck) |

If `model-service` has `PROCESS_TYPE=beat`, the next restart serves Celery instead of uvicorn and the site boards die.

## One-button deploy

From repo root (Railway CLI logged in):

```bash
bash scripts/deploy-railway-model-service.sh --wait
```

Or push to `deploy-vercel` with paths under `services/model-service/**` → GitHub Action `.github/workflows/deploy-railway.yml`.

Always:

```text
railway up services/model-service --path-as-root
```

Dashboard `rootDirectory` must stay **empty** when using path-as-root.

## Season refresh knobs (env)

| Variable | Default (pre-season) | Meaning |
| --- | --- | --- |
| `ODDS_PULL_ACTIVE_MINUTE_PATTERN` | `0` | Odds at :00 each hour 7–23 |
| `ODDS_PULL_LATE_START/END_HOUR` | `3` / `3` | Single 3:00am odds pull |
| `NFL_SEASON_BOARD_REFRESH_MINUTE` | `15` | Light sims at :15 each hour 7–23 |
| `NFL_CONTEXT_REFRESH_MINUTE` | `20` | Context at :20 each hour 7–23 |
| `NFL_SIM_3AM_COUNT` | `4000` | Fuller sims in the 3:15am refresh |
| `NFL_PRODUCT_GATE_STATUS` | `YELLOW` | Selective PLAY |

In-season: set `ODDS_PULL_ACTIVE_MINUTE_PATTERN=*/5` (or `*/10`) around report windows only.

## Smoke checks after deploy

```bash
curl -sS https://model-service-production-e253.up.railway.app/health
curl -sS 'https://model-service-production-e253.up.railway.app/nfl/fair-lines?limit=3' | head -c 400
```

## Rollback

Redeploy previous successful deployment in Railway UI per service, or `git revert` + one-button script.

## Do not

- Point GitHub auto-build at monorepo root Dockerfile
- Put `/health` on worker/beat
- Set API `PROCESS_TYPE` to anything but `api`
- Burn historical odds densify for routine refreshes
