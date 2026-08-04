# NFL Season Engine v1.6 — Stronger Game-Script / Play-Calling

**Date:** 2026-08-03  
**Engine version before:** `nfl-season-engine-v1.5-depth-volatility`  
**Engine version after:** `nfl-season-engine-v1.6-game-script`  
**Package:** `services/model-service/src/services/nfl_season_engine/`  
**Artifact JSON:** `data/ops/nfl-season-engine-game-script-20260803.json`

## Goal

Make Layer 2 (game script) and implied play-calling more realistic so that
pass/run balance shifts with score + time, usage reacts more sharply via the
existing `SCRIPT_USAGE_MATRIX`, and production follows those volume shifts —
without breaking depth-chart volatility, injury shocks, survivor, or the
four-layer hierarchy.

## What changed

### 1. Richer script classification (`game_script.py`)

Score differential → fine **script detail**:

| Detail | Margin (own − opp) |
| --- | --- |
| `large_lead` | ≥ +14 |
| `small_lead` | ≥ +4 |
| `neutral` | (−4, +4) |
| `small_deficit` | ≤ −4 |
| `large_deficit` | ≤ −14 |

Coarse `lead` / `trail` / `neutral` is preserved for Layer 3/4 compatibility
(`coarse_script()`).

Representative remaining clock (seeded) → **time bucket**:

| Bucket | Minutes remaining |
| --- | --- |
| `early` | > 40 |
| `mid` | 20–40 |
| `late` | ≤ 20 |

**Intensity** ∈ [0, 1] from |margin| × late-clock pressure.

### 2. Explicit play-mix outputs

Per side on `GameScript`:

- `pass_rate` / `run_rate`
- `early_down_pass_rate`
- `hurry_up` (0–1 proxy; trailing late)
- `script_detail`, `script_intensity`, shared `time_bucket` / `minutes_remaining`

Trailing late raises pass rate + hurry-up; protecting a late lead lowers pass
rate and early-down pass rate. Force hooks for ops/tests:
`force_home_score`, `force_away_score`, `force_minutes_remaining`,
`force_home_detail`, `force_away_detail`.

### 3. Sharper usage reactions (`usage_roles.py`)

Same `SCRIPT_USAGE_MATRIX` (not a parallel system), sharpened + intensity-scaled:

| Script | RB1 rush | WR1 tgt | TE1 tgt | WR3 tgt |
| --- | --- | --- | --- | --- |
| **trail** | ×0.80 | ×1.20 | ×1.16 | ×0.90 |
| **lead** | ×1.24 | ×0.94 | ×0.96 | ×0.78 |
| **neutral** | ×1.0 | ×1.0 | ×1.0 | ×1.0 |

Scale: `(0.40 + 1.10×intensity) × {early:0.55, mid:0.90, late:1.30}` clamped
to [0.30, 1.85]. Tiny `SCRIPT_DETAIL_EXTRA` for `large_lead` / `large_deficit`.

### 4. Production

No new opaque efficiency stack. Existing thin trail/lead YPA/YPC nudges are
intensity-scaled so volume (Layers 2–3) remains the primary script channel.

### 5. Diagnostics (additive)

`include_diagnostics=true` on game-boxes adds:

- `play_mix_home` / `play_mix_away` (MC means + modal detail/bucket)
- `play_mix_sample` (first replicate inspectable dict)
- richer `game_script_summary` (early-down pass, hurry-up, late rate, …)

Player rows: additive `script_detail`.

## Before / after — trailing late vs protecting lead

Forced KC home script, late clock (6:00), same seed family (demo universe).

| Metric | Trailing late (`large_deficit` 10–28) | Protecting lead (`large_lead` 28–10) |
| --- | --- | --- |
| `pass_rate` | **0.71** | **0.50** |
| `early_down_pass_rate` | 0.68 | 0.52 |
| `hurry_up` | **0.89** | **0.00** |
| RB1 carries | **5.9** | **26.9** |
| WR1 targets | **14.5** | **6.8** |
| TE1 targets | **9.4** | **4.9** |
| Mahomes pass yds | ~288 | ~201 |
| KC RB rush yds | ~23 | ~106 |
| Rice rec yds | ~93 | ~45 |

Forced extremes exaggerate late-game script; marginal BUF@KC MC stays in
sanity bands (below).

## BUF @ KC marginal (200 reps, seed 2026)

| Player | Point estimate |
| --- | --- |
| P.Mahomes | 242 pass yds, 1.69 TD, 0.53 INT |
| J.Cook | 54 rush yds, 2.7 rec |
| R.Rice | 5.5 rec, 60 rec yds |

`play_mix_home.pass_rate_mean` ≈ 0.60; `time_bucket_late_rate` ≈ 0.43.

## Remaining limitations

- Game-level analytic clock snapshot — **not** drive-by-drive temporal sim
- No coaching tendencies / red-zone specials (out of scope)
- Intensity scaling can push forced late blowouts to extreme RB/WR splits;
  marginal MC averages remain bounded
- Production efficiency still thin league-ish when baselines missing

## Tests

`services/model-service/tests/test_nfl_season_engine_game_script.py`

- Trailing late pass_rate > leading late
- Leading late ↑ RB1 carries vs trailing
- Trailing ↑ WR1/TE targets vs leading
- Injury + depth chart still work under new scripts
- BUF@KC realism + diagnostics play-mix fields
- Forced-script determinism

## Files touched

- `game_script.py`, `types.py`, `usage_roles.py`, `player_usage.py`, `production.py`
- `game_query.py`, `calibration.py`, `__init__.py`
- `routes/nfl.py` (status capabilities / game_script block)
- Tests + this ops note + foundation/api-contract updates

## Railway

Merged PR #80 → `deploy-vercel`; Railway `model-service` (`brave-art` /
`model-service-production-e253`) redeployed and smokes green:

- `GET /nfl/season-engine/status` → `nfl-season-engine-v1.6-game-script` +
  `game_script_play_mix` capability + `game_script` block
- `GET .../game-boxes?...&include_diagnostics=true` → `diagnostics.play_mix_home`
  / `play_mix_away` / `play_mix_sample` with `pass_rate`, `early_down_pass_rate`,
  `hurry_up`, `script_detail`, `script_intensity`

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status" \
  | jq '.engine_version, .capabilities, .game_script'
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/game-boxes?home_team=KC&away_team=BUF&week=1&demo=true&n_replicates=80&include_diagnostics=true" \
  | jq '{engine_version, play_mix_home: .diagnostics.play_mix_home, play_mix_sample: .diagnostics.play_mix_sample.home}'
```
