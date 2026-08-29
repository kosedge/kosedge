# Model Tracker — CFB Week 0 desk runbook

**Doc:** `data/ops/model-performance-tracker-v1-20260829.md`  
**APIs:** `/model-tracker/*` on model-service  
**UI:** `/pro/cfb/tracker` · `/pro/model-tracker`

## Unit rules

- **PLAY** = 1 unit (PnL + ROI)
- **LEAN** = 0 units (still graded for hit-rate)
- Default juice −110

## Log a PLAY (curl)

```bash
export MODEL_SERVICE_URL="${MODEL_SERVICE_URL:?set MODEL_SERVICE_URL}"

curl -sS -X POST "$MODEL_SERVICE_URL/model-tracker/picks" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{
    "sport": "cfb",
    "season": 2026,
    "week": 0,
    "home_team": "TCU",
    "away_team": "UNC",
    "game_id": "401856766",
    "market_type": "spread",
    "side": "home",
    "line_at_publish": -3.5,
    "tag": "PLAY",
    "edge_pts": 4.2,
    "engine_version": "cfb-season-engine-v0.9-inseason",
    "kei_version": "cfb-kei-v1.0-2026w0",
    "created_by": "desk",
    "source": "manual"
  }'
```

## Log a LEAN

Same payload with `"tag": "LEAN"`. Units stay 0.

## KEI board dry-run import

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/model-tracker/cfb/import-kei-board" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"weeks":[0,1],"dry_run":true}'
```

Packaged KEI often has `market_spread_home: null` → PASS → 0 candidates. Desk logs from Edge Board once books are joined.

## Grade after final

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/model-tracker/picks/$ID/close" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"line_at_close": -6.5}'

curl -sS -X POST "$MODEL_SERVICE_URL/model-tracker/picks/$ID/grade" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"home_score": 31, "away_score": 24}'
```

## Summary

```bash
curl -sS "$MODEL_SERVICE_URL/model-tracker/summary?sport=cfb&season=2026" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"
```

## Honesty

Internal desk tracker only. Does **not** turn on public NFL props PLAY chrome.
