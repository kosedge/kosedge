# CFB Performance Tracking + CLV Logging (v0.8.2)

**Date:** 2026-08-05  
**Engine version:** `cfb-season-engine-v0.8.2-tracking`  
**Calibration tag (priors unchanged):** `cfb-season-engine-priors-v0.8.1-hist-cal`  
**Migration:** `infra/db/049_cfb_performance_tracking.sql`

## Purpose

Log every meaningful project-game output against the closing line and final score so the season engine can be measured continuously. This is **live paper tracking** — complementary to the historical closing-line backtest in `cfb-historical-calibration-20260805.md`.

Does **not** invent KEI or change Edge Board markets-only behavior. Projection knobs are unchanged from v0.8.1; this is a capability / schema bump.

## How to use

### 1. Log a projection

```bash
# From an existing project-game payload (or minimal fields)
curl -sS -X POST "$MODEL_SERVICE_URL/cfb/season-engine/projections/log" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{
    "home_team": "ALA",
    "away_team": "UGA",
    "season": 2026,
    "week": 1,
    "spread_home": -3.5,
    "expected_total": 51.0,
    "home_win_prob": 0.58,
    "away_win_prob": 0.42,
    "expected_home_score": 27.0,
    "expected_away_score": 24.0,
    "drivers": {"summary": {}}
  }'
```

Or opt in on project-game (sync, returns `projection_log_id`):

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/cfb/season-engine/project-game" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"home_team":"TEX","away_team":"OU","week":1,"demo":true,"log_projection":true}'
```

Optional auto-log (async / best-effort, never blocks happy path):

```bash
export CFB_AUTO_LOG_PROJECTIONS=1
```

### 2. Capture close (manual OK)

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/cfb/season-engine/projections/$ID/close" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"close_spread_home": -6.5, "close_total": 49.0, "source": "manual"}'
```

### 3. Capture result

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/cfb/season-engine/projections/$ID/result" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"home_score": 31, "away_score": 24, "source": "manual"}'
```

### 4. Summary

```bash
curl -sS "$MODEL_SERVICE_URL/cfb/season-engine/performance" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"
```

## Schema

### Postgres (`cfb_projection_logs`)

| Column | Notes |
|--------|-------|
| `id` | UUID |
| `game_key` | `{season}-W{week:02d}-{away}@{home}` |
| `engine_version` | Always stamped |
| `model_spread_home` / `model_total` / WP / scores | From project-game |
| `drivers` / `projection` | JSONB snapshots |
| `close_*` / `spread_clv` / `total_clv` | Set on close |
| `home_score` / `away_score` / `grade_*` | Set on result |

Apply: `psql "$DATABASE_URL" -f infra/db/049_cfb_performance_tracking.sql`

### JSONL fallback

Default lake: `data/ops/cfb_projection_logs/projections.jsonl`  
Override: `CFB_PROJECTION_LOG_DIR`  
Backend: `CFB_PROJECTION_LOG_BACKEND=jsonl|db|auto` (default `auto`).

- Always writes JSONL.
- Postgres upsert only when `CFB_PROJECTION_LOG_DB=1` (or `BACKEND=db`) — off by default because Railway Postgres has been flaky.

When DB is unreachable or disabled, JSONL remains the durable source for summary.

## CLV definition

Spreads are **home-relative** (negative = home favored), same as project-game / hist-cal.

```
spread_clv = model_spread_home − close_spread_home
```

- **Positive** = beat the close on the home-side price  
  (e.g. model −3, close −7 → CLV +4)
- **Negative** = model was more home-favoring than the market closed

```
total_clv = model_total − close_total
```

## Grading

| Market | Rule |
|--------|------|
| **ATS** | Prefer close line; else model spread. Grade the model's preferred side (≥0.5 pt edge). Home covers if `actual_margin + line > 0`. |
| **O/U** | Prefer close total; else model. Model over when `model_total > line + 0.5`. |
| **SU** | Model home when `home_win_prob ≥ 0.5`; win if that matches final winner. |

## Endpoints

| Method | Path |
|--------|------|
| POST | `/cfb/season-engine/projections/log` |
| POST | `/cfb/season-engine/projections/{id}/close` |
| POST | `/cfb/season-engine/projections/{id}/result` |
| GET | `/cfb/season-engine/performance` |

Also: `log_projection: true` on `POST /cfb/season-engine/project-game`.

## UI

Thin performance strip on `/pro/cfb/model` (record / CLV / error). Full project-game UX unchanged.

## Honesty

- Tracking is as good as the closes/results you enter (manual first).
- Hist-cal ≠ live CLV; do not conflate backtest ATS proxy with paper CLV.
- No Edge Board KEI invent from these logs.
