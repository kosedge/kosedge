# Model Performance + Pick/Unit Tracker v1

**Date:** 2026-08-29  
**Branch:** `cursor/model-performance-tracker-7d1e` → `deploy-vercel`  
**Migration:** `infra/db/053_model_pick_ledger.sql`  
**Engine surface:** `/model-tracker/*` (sport-agnostic) + CFB desk adapters  
**Web:** `/pro/model-tracker`, `/pro/cfb/tracker`

## Purpose

Enterprise desk ledger for **plays vs leans**, **unit bankroll**, and **model performance instrumentation** across sports. Starts with **CFB Week 0–1 2026**; schema/APIs are sport-agnostic so NFL/NBA/MLB/WNBA hang off the same core without a rewrite.

This is **tracking / grading**, not public “play this” chrome.

- Does **not** ungate NFL props PLAY/LEAN stake tags (`NFL_WEEKLY_PROPS_LIVE` policy unchanged).
- Complements the existing **proof lake** (`proof_projections` / `/proof/*` / `/cfb/season-engine/performance`) which logs research projections + CLV/grades.
- Pick ledger = desk-tagged PLAY/LEAN with unit accounting; optional FK to a proof projection row.

## Unit rules (hard)

| Tag | Units risked | Counts toward W-L-P | ROI (units) |
|-----|--------------|---------------------|-------------|
| **PLAY** | **1.0** (default; override only via explicit `units` if stake policy approved later) | Yes | Yes |
| **LEAN** | **0.0** | Yes (hit-rate / training signal) | No (always 0 PnL) |
| PASS | Not logged as a pick | — | — |

- Default American odds **-110** → win pays `100/110 ≈ 0.9091` units on a 1u PLAY.
- Push / void → 0 units PnL; void does not count as W or L (separate grade).
- Cumulative unit curve = running sum of PLAY `units_pnl` ordered by `graded_at` (fallback `published_at`).

## Schema (`model_pick_ledger`)

Sport-agnostic graded rows. Key columns:

- Identity: `id`, `sport`, `season`, `week`, `slate_id`, `game_id`, `game_key`
- Market: `market_type` (`spread|total|moneyline|prop`), `side`, `line_at_publish`, `odds_american`
- Tag: `tag` (`PLAY|LEAN`), `units` (1 or 0)
- Model: `engine_version`, `artifact_as_of`, `deploy_git_sha`, `kei_version`, `fair_line`, `edge_pts`, `kei_line`, `confidence`, `variance`, `confirmation`, `info_overlap`
- Close: `line_at_close`, `close_captured_at`, `clv`, `open_to_close_move`
- Result: `home_score`, `away_score`, `result_detail`, `grade` (`win|loss|push|void|pending`), `graded_at`, `units_pnl`
- Audit: `created_by` (`desk|system`), `source` (`manual|kei_board|auto`), `created_at`, `updated_at`, `notes`, `payload` JSONB
- Proof link: `proof_projection_id` (optional UUID → `proof_projections.id`)

JSONL fallback: `services/model-service/data/ops/model_pick_ledger/picks.jsonl`  
Backend: `MODEL_TRACKER_BACKEND=jsonl|db|auto` (default `auto`, same durability story as proof lake).

## APIs

| Method | Path | Role |
|--------|------|------|
| GET | `/model-tracker/status` | Health + backend + counts |
| POST | `/model-tracker/picks` | Log PLAY/LEAN |
| GET | `/model-tracker/picks` | List/filter |
| GET | `/model-tracker/picks/{id}` | Fetch one |
| POST | `/model-tracker/picks/{id}/close` | Capture closing line + CLV |
| POST | `/model-tracker/picks/{id}/grade` | Grade from scores / explicit grade |
| GET | `/model-tracker/summary` | Record, units, ROI, curve, by model/sport/week |
| GET | `/model-tracker/export` | JSON/CSV training dump |
| POST | `/model-tracker/cfb/import-kei-board` | Import PLAY/LEAN rows from packaged KEI board (desk confirm) |
| GET | `/model-tracker/sports` | Supported sports + adapter status |

CFB thin aliases (optional): status already exposes tracker under proof docs; desk uses shared `/model-tracker`.

## CFB day-1 ops (Week 0 tip-off)

1. Ensure model-service is healthy; check `GET /model-tracker/status`.
2. Review Edge Board / packaged KEI (`cfb_kei_w0_w1_2026.json`). Only rows with live market + PLAY/LEAN tags are import candidates.
3. **Desk logs** via UI (`/pro/cfb/tracker`) or:

```bash
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
    "source": "manual",
    "created_by": "desk"
  }'
```

4. LEAN example: same payload with `"tag": "LEAN"` → `units=0`, still graded for hit-rate.
5. After kickoff / final:

```bash
# Close (optional but preferred for CLV)
curl -sS -X POST "$MODEL_SERVICE_URL/model-tracker/picks/$ID/close" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"line_at_close": -6.5, "source": "manual"}'

# Grade
curl -sS -X POST "$MODEL_SERVICE_URL/model-tracker/picks/$ID/grade" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"home_score": 31, "away_score": 24, "source": "manual"}'
```

6. Summary / curve: `GET /model-tracker/summary?sport=cfb&season=2026`

Seed helper: `python -m scripts.model_tracker_smoke` (or `services/model-service` test path) — see `scripts/ops/model-tracker-cfb-week0.md`.

## Sport extension plan

| Sport | Day-1 | Adapter |
|-------|-------|---------|
| **CFB** | Live | KEI board import + manual desk log; grades from scores |
| **NFL** | Stub | Same ledger; import from side/total publish policy **only when desk explicitly logs** — do not auto-publish props PLAY chrome |
| **NBA / MLB / WNBA** | Stub | Feature flag `MODEL_TRACKER_SPORTS`; routes accept sport code; adapters return `status: stub` until wired |

Extension checklist per sport:

1. Map game_id / slate_id conventions.
2. Wire publish-line + KEI/fair fields into `log_pick` payload (no second projection engine).
3. Close/result hooks from existing odds/outcomes jobs when ready.
4. Enable sport on `/model-tracker/sports` + desk filter.

## Separation of concerns

```
proof_projections     → research fair vs close vs result (model calibration)
model_pick_ledger     → desk PLAY/LEAN with units (desk P&L + training labels)
public props boards   → numbers / edge only unless stake policy separately approved
```

## Honesty / gaps (v1)

- Auto-grade from live scores: **manual or ops-triggered** in v1 (no silent score poll yet).
- KEI board import skips PASS and rows without a market line.
- ROI assumes flat 1u @ listed odds; no Kelly / book variance yet.
- Multi-book “best line” is stored on the pick when provided; CLV uses the recorded close for that market.
