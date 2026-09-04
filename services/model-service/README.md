# Model Service — Deployment

FastAPI app (`src/main.py`) plus Celery tasks (`src/tasks.py`) scheduled by
`src/celerybeat_schedule.py`. Locally, and previously in production, only the
web process (`uvicorn`) was running — **the celery worker and beat scheduler
were never actually deployed**, so the "every 30 min" odds-pull schedule in
`celerybeat_schedule.py` existed in code but never ran. This needs **three**
Railway services from this same repo/Dockerfile, each with a different start
command:

| Service  | Start command                                                     | Config file           |
| -------- | ----------------------------------------------------------------- | --------------------- |
| `api`    | `uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}`        | `railway.json`        |
| `worker` | `celery -A src.celery_app worker --loglevel=info --concurrency=4` | `railway.worker.json` |
| `beat`   | `celery -A src.celery_app beat --loglevel=info`                   | `railway.beat.json`   |

Railway doesn't support defining multiple services from one config file —
create each service in the dashboard (same repo, same Dockerfile), then
either set the **Custom Start Command** directly in that service's settings,
or point its **Config File** setting to the matching `railway.*.json` above.

## Required environment variables (all three services need these)

- `DATABASE_URL` — Postgres connection string.
- `REDIS_URL` / `CELERY_BROKER_URL` — needed by `worker` and `beat` (a Redis
  instance; Railway's Redis plugin works). Not needed by `api` unless it also
  enqueues tasks.
- `ODDS_API_KEY` — [the-odds-api.com](https://the-odds-api.com). Must match
  what's set in the `apps/web` Vercel project's `ODDS_API_KEY` — they're
  billed against the same account/credits, so use one key everywhere, not
  separate keys per service.
- `ODDS_API_KEY_BACKUP` — optional fallback if the primary key is rate-limited
  or revoked (see `services/odds_api.py`).

### Optional — Visual Crossing weather (NFL H travel×weather)

H (`travel_weather_interaction`) already runs on Open-Meteo → climatology when
no VC key is present. Adding a key upgrades stadium-day weather quality.

1. Sign up / get a free key: [Visual Crossing Weather API](https://www.visualcrossing.com/weather-api)
2. Set **`VISUAL_CROSSING_API_KEY`** on local `.env` and Railway **model-service**
   (production). Alias `VISUALCROSSING_API_KEY` also works.
3. Leave `NFL_VC_WEATHER_ENABLED=true` (default). Disable to force Open-Meteo.
4. Free tier is ~**1000 requests/day**. Production path caches by
   location+date (~18h TTL in `nfl_dp_weather_forecast_cache`) and spaces
   network calls (~1.1s min interval).

Dry-run (no network when key missing):

```bash
cd services/model-service
python -m data_platform_nfl.cli --print-external-source-status
```

## Odds API credit budget — read before turning the scheduler on

The default schedule in `celerybeat_schedule.py` pulls live odds every 30
minutes from 7am–9pm and hourly overnight (`pull-odds-every-30-min-active`,
`pull-odds-hourly-late`), across 4 sports (NFL/NBA/MLB/NCAAB) each pull. That
is roughly **150 credits per pull × ~28 pulls/day ≈ 4,200 credits/day**. A
20,000-credit key lasts under 5 days at that cadence. Before enabling `beat`
in production, either:

- Reduce cadence (e.g. `ODDS_PULL_ACTIVE_MINUTE_PATTERN=*/90` for every 90
  min instead of every 30), or
- Restrict `pull_odds_snapshot` to fewer sports if you don't need all four
  tracked live, or
- Budget for a recurring credit top-up at the current cadence.

Historical backfills (`pull_historical_odds_backfill`, used for the CLV
report in `data/ops/nfl-clv-benchmark-report.json`) are one-off, not
scheduled — they don't recur automatically and won't silently burn credits.

## Local dev

```bash
# from services/model-service, with a local Redis running:
export DATABASE_URL="postgresql+psycopg://<user>:<pass>@127.0.0.1:5432/kosedge"
export CELERY_BROKER_URL="redis://127.0.0.1:6379/0"
export ODDS_API_KEY="..."

celery -A src.celery_app worker --loglevel=info --concurrency=2 -Q odds,models,nfl_market,celery &
celery -A src.celery_app beat --loglevel=info -s /tmp/celerybeat-schedule &
```

### NFL market-history queue (`nfl_market`)

`materialize_nfl_market_history` is routed to the dedicated **`nfl_market`**
queue (env `CELERY_NFL_MARKET_QUEUE`, default `nfl_market`) so NBA/models
backlog cannot starve append-only ledger writes. Production worker must
consume it:

- Dockerfile default: `-Q ${CELERY_WORKER_QUEUES:-default,odds,models,nfl_market}`
- If Railway overrides `CELERY_WORKER_QUEUES`, append `,nfl_market` and
  redeploy/restart the worker (+ beat so schedule options pick up the queue).

Or call any task directly without a broker, e.g. for one-off backfills:

```python
from src.tasks import pull_odds_snapshot
pull_odds_snapshot.run()
```
