# Railway season ops (brave-art)

## Mental model (critical)

| Cadence | What runs | What does **not** |
| --- | --- | --- |
| **Every 5–10 min** | Celery **beat** → odds pull + NFL board refresh (sims/context) | Container redeploy |
| **On code change** | One-button / CI `railway up --path-as-root` for api+worker+beat | — |
| **Weekly** | Enterprise sharpening, retrain, DR | — |

Redeploying every 5–10 minutes is wrong and will thrash the site. **Data refresh ≠ deploy.**

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

| Variable | Default | Meaning |
| --- | --- | --- |
| `ODDS_PULL_ACTIVE_MINUTE_PATTERN` | `*/10` | Odds every 10 min (set `*/5` on heavy gamedays) |
| `NFL_SEASON_BOARD_REFRESH_MINUTE` | `*/10` | Light NFL sims for fair-lines |
| `NFL_SEASON_BOARD_SIM_COUNT` | `1500` | Sims per board refresh (keep modest) |
| `NFL_CONTEXT_REFRESH_MINUTE` | `7,37` | Context twice per hour in season window |
| `NFL_PRODUCT_GATE_STATUS` | `YELLOW` | Selective PLAY |

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
