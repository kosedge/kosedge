# CFB In-Season Updating Foundation (v0.9)

**Engine:** `cfb-season-engine-v0.9-inseason`  
**Date:** 2026-08-05  
**Status:** Foundation (manual / tracking-tied ingest). Not a fully automated live pipeline.

## Goal

Let completed games move team efficiency (and thus project-game lines) week to week, instead of staying frozen on preseason SP+ + roster priors — with shrinkage so one weird game cannot destroy a rating.

## How it works

1. **Baseline** — Packaged final-2025 SP+ `off_eff` / `def_eff` remain the preseason prior (`build_efficiency_profile(..., apply_inseason=False)`).
2. **Ingest** — `POST /cfb/season-engine/in-season/ingest-result` (or `projections/{id}/result` with `apply_inseason=true`).
3. **Residual** — `actual_margin_home − expected_margin_home`  
   - `actual_margin_home = home_score − away_score`  
   - `expected_margin_home = −model_spread_home` (or expected scores if provided)  
   - Clamped to ±28 pts.
4. **Split** — 55% of residual → home offense / away defense; 45% → away offense / home defense (signed).
5. **Scale** — `Δ = residual × 0.35 × week_weight × learning_rate`  
   - `week_weight`: W1=1.00 → W4=0.76 → late≈0.38  
   - `learning_rate = 0.55 / (1+n_games)^0.65`  
   - Per-game |Δeff| capped at **3.5**  
   - Cumulative |Δ| capped at **12**  
   - Mild late-season pull toward prior (shrinkage).
6. **Apply** — Deltas added inside `build_efficiency_profile` so project-game / season-sim pick them up when the universe is rebuilt.
7. **State** — JSON snapshot (`CFB_INSEASON_STATE_PATH` or `/app/data/ops/cfb_inseason_state/state.json`). Preseason vs current always inspectable.

## Example (illustrative)

UGA home, model spread −28, final 24–21 (won but underperformed):

| | Before | After (W1 ingest) |
|---|---:|---:|
| UGA `off_eff` | preseason | preseason + modest negative Δ |
| UGA `delta_off_eff` | 0 | ~−2 to −3.5 (clamped) |
| BALL `def_eff` | preseason | slightly up (held UGA under model) |

A W1 blowout *over* the model moves the favorite’s offense up; the same residual in W12 moves less.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/cfb/season-engine/in-season/ingest-result` | Apply one result |
| GET | `/cfb/season-engine/in-season/state` | Full state |
| GET | `/cfb/season-engine/in-season/team/{team}` | One team |
| POST | `/cfb/season-engine/in-season/reset` | Clear deltas (`confirm=true`) |
| POST | `/cfb/season-engine/projections/{id}/result` | Tracking grade; optional `apply_inseason` |

## Limitations

- Foundation only — no auto weekly job, no opponent-adjusted PBP residual yet.
- Moves efficiency only (not roster/QB identity layers).
- Expected margin needs a model spread or expected scores; otherwise residual vs 0.
- State is local JSON on the API instance (not multi-replica shared unless path is shared volume/DB later).
- Idempotent on `game_id` only — re-ingest with a new id will apply again.

## Files

- `services/model-service/src/services/cfb_season_engine/in_season_update.py`
- Wired: `efficiency.py`, `performance_tracking.py`, `routes/cfb.py`, `priors.py`, `__init__.py`
- Tests: `tests/test_cfb_in_season_update.py`
