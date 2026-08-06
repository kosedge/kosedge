# Unified Proof Layer — Projection Logging + CLV + Results (NFL + CFB)

**Date:** 2026-08-06  
**Branch:** `feat/unified-proof-layer`  
**Module:** `services/model-service/src/services/proof_layer/`

## Purpose

Subscription-grade measurement: every important projection is logged, closable, and gradable. NFL and CFB share one JSONL lake with a `sport` field. CFB legacy endpoints remain as thin wrappers.

## Quick start

### 1. Log a projection (unified)

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/proof/projections" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{
    "sport": "cfb",
    "market_type": "game",
    "home_team": "ALA",
    "away_team": "UGA",
    "season": 2026,
    "week": 1,
    "spread_home": -3.5,
    "expected_total": 51.0,
    "home_win_prob": 0.58
  }'
```

NFL via season-engine game-boxes (opt-in):

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/game-boxes?home_team=KC&away_team=BUF&week=1&demo=true&log_projection=true" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"
```

Or POST with body `{ "log_projection": true }`.

### 2. Capture close

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/proof/projections/$ID/close" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"close_spread_home": -6.5, "close_total": 49.0, "source": "manual"}'
```

### 3. Capture result

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/proof/projections/$ID/result" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"home_score": 31, "away_score": 24, "source": "manual"}'
```

CFB in-season rating update (optional):

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/proof/projections/$ID/result" \
  -H "Content-Type: application/json" \
  -d '{"home_score": 31, "away_score": 24, "apply_inseason": true}'
```

### 4. Performance summary

```bash
curl -sS "$MODEL_SERVICE_URL/proof/performance?sport=nfl" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"

curl -sS "$MODEL_SERVICE_URL/proof/performance?sport=cfb&engine_version=cfb-season-engine-v0.9-inseason" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"
```

## Unified API

| Method | Path |
|--------|------|
| POST | `/proof/projections` |
| POST | `/proof/projections/{id}/close` |
| POST | `/proof/projections/{id}/result` |
| GET | `/proof/performance?sport=nfl\|cfb&engine_version=...` |
| GET | `/proof/docs` |

## CFB compatibility (unchanged paths)

| Method | Path |
|--------|------|
| POST | `/cfb/season-engine/projections/log` |
| POST | `/cfb/season-engine/projections/{id}/close` |
| POST | `/cfb/season-engine/projections/{id}/result` |
| GET | `/cfb/season-engine/performance` |

## Storage

**Default lake:** `services/model-service/data/ops/projection_logs/projections.jsonl`  
(Railway `--path-as-root` → `/app/data/ops/projection_logs/`; falls back to `/tmp/kosedge_projection_logs`.)

| Env | Purpose |
|-----|---------|
| `PROJECTION_LOG_DIR` | Unified lake directory |
| `PROOF_LAYER_LOG_DIR` | Alias |
| `CFB_PROJECTION_LOG_DIR` | Optional CFB-only override (legacy) |
| `PROJECTION_LOG_BACKEND` | `jsonl` \| `db` \| `auto` |
| `CFB_PROJECTION_LOG_DB=1` | Opt-in Postgres mirror (CFB only) |
| `PROOF_AUTO_LOG_PROJECTIONS=1` | Auto-log all sports (async) |
| `CFB_AUTO_LOG_PROJECTIONS=1` | Auto-log CFB |
| `NFL_AUTO_LOG_PROJECTIONS=1` | Auto-log NFL game-boxes |

## Schema (JSONL record)

| Field | Notes |
|-------|-------|
| `sport` | `nfl` \| `cfb` |
| `market_type` | Default `game` (spread/total/wp) |
| `id` | UUID |
| `game_key` | `{season}-W{week:02d}-{away}@{home}` |
| `engine_version` | Stamped per sport engine |
| `model_spread_home` / `model_total` / WP | From projection |
| `close_*` / `spread_clv` / `total_clv` | Set on close only |
| `home_score` / `away_score` / `grade_*` | Set on result |

## CLV (honest)

```
spread_clv = model_spread_home − close_spread_home   # only when close exists
total_clv  = model_total − close_total
```

Positive spread CLV = beat the close on the home-side price. No close → no CLV.

## Grading

| Market | Rule |
|--------|------|
| **ATS** | Prefer close line; else model spread. Grade model's preferred side (≥0.5 pt edge). |
| **O/U** | Prefer close total; else model. |
| **SU** | Model home when `home_win_prob ≥ 0.5`. |

## NFL ingest path

Primary: `GET|POST /nfl/season-engine/game-boxes` with `log_projection=true`.  
Spread derived from simulated expected scores in `game_script_summary`.

## Tests

```bash
cd services/model-service
pytest tests/test_proof_layer.py tests/test_cfb_performance_tracking.py -q
```

## Honesty

- Tracking quality depends on closes/results you enter.
- CLV requires closes — never invented.
- Does not change Edge Board KEI or live projection math; logging is fire-and-forget.
