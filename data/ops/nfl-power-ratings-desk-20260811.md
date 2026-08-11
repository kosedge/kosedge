# NFL Power Ratings Desk + Early-Season Shrinkage — 2026-08-11

Branch: `feat/nfl-power-ratings-desk` → `deploy-vercel` (+ Railway model-service).

Depends on: single strength path (#196 LAR, #197 DET merged).

## Doctrine

| Rule | Implementation |
|------|----------------|
| Model PR from the model | Method **B** — `expected_team_points` vs synthetic avg opponent, zero-centered |
| Ryan never overwrites Model | `ryan_pr = model_pr + ryan_adj`; adj defaults **0** |
| No EPA/QB/OL/SOS double-count | Components read Layer-1 indices only |
| Same `active_run_id` | From `data/ops/nfl-web-launch-bundle.json` |
| Early-season Bayesian shrink | `PR = (1−α)·prior + α·data` — Model PR only |
| Tuesday publish (ET) | After prior week finals; cutoff **Tue 06:00 ET** |

## Method A / B / C

| Method | Status |
|--------|--------|
| **A** — 496 pairwise margins | Not used (heavy); reserved |
| **B** — vs league-average opponent | **Chosen** |
| **C** — map index → points + center | Fallback only if B unavailable |

Module: `services/model-service/src/services/nfl_season_engine/power_ratings_desk.py`

## α schedule (config)

Source: `ALPHA_BY_WEEK` in `power_ratings_desk.py`

| After week | α (new data) | Prior share |
|------------|--------------|-------------|
| 1 | 0.12 | ~88% |
| 2 | 0.20 | ~80% |
| 3 | 0.30 | ~70% |
| 4 | 0.40 | ~60% |
| 5–8 | 0.50 → 0.70 | ramp |
| 9+ | 0.80 (cap 0.90) | majority data |

Shrink-more multipliers: backup QB, tiny sample, extreme script, missing injury info.

## Table columns shipped

Team · Model PR · Ryan Adj · Ryan PR · Market PR · Δ Mkt · Off · Def · ST · Active PR · Unc. · Prev Week · Weekly Δ

- **Market PR / Δ Mkt** — — until futures/win-total implied powers wired (best effort)
- **ST** — labeled approximate (`st_index`)
- **Prev / Weekly Δ** — — in preseason until a prior Tuesday snapshot exists

## Base / Active / Game

| State | Meaning |
|-------|---------|
| Base PR | Ryan PR if adj ≠ 0, else Model PR |
| Active PR | Method B on injury-aware indices + Ryan Adj |
| Game PR | Edge Board path only — not stored on this desk |

## Ryan Adj policy

±0.25 routine · ±0.5 meaningful · ±1.0 major · **>1.0** needs written reason.  
File: `data/ops/nfl-power-ratings-desk/ryan_adj.json` (all zeros at ship).

## Tuesday job

- Script: `scripts/nfl/tuesday_power_ratings_update.py`
- Wrapper: `scripts/nfl/run-tuesday-power-ratings-update.sh`
- Runbook: `docs/runbooks/nfl-tuesday-power-ratings.md`
- Preseason: `WEEK=0` snapshot / no-op shrink
- Audit: `data/ops/nfl-power-ratings-desk/tuesday-audit-week*.json`

## API / UI

| Piece | Path |
|-------|------|
| Serializer | `power_ratings_desk.serialize_power_ratings_desk` |
| Upstream | `GET /nfl/season-engine/power-ratings` |
| Web | `/pro/power-ratings/nfl` reads `latest.json` |
| True PR drivers | `/pro/nfl/model` (unchanged) |

## Coherence

Wins / playoff / SB / production stay on the same strength path.  
Edge Board Model → KEI → tag **unchanged**.

## Tests

`services/model-service/tests/test_nfl_power_ratings_desk.py`

- Week 1 extreme PR_data → small move
- Week 10 same shock → larger move
- mean(Model PR) ≈ 0 after shrink / derive
- Ryan adj default 0; LA→LAR one row
