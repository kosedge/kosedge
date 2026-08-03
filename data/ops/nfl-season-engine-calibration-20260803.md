# NFL Season Engine — Calibration Pass

**Date:** 2026-08-03  
**Branch:** `nfl-season-engine-calibration` → `deploy-vercel`  
**Base:** PR #71 hierarchical Full NFL Model (`nfl-season-engine-v1`)  
**Engine version after:** `nfl-season-engine-v1.1-calibrated`  
**Calibration tag:** `nfl-season-engine-cal-v1`  
**Scope:** Additive calibration of `nfl_season_engine` only. No injury shocks, no deeper usage features, no survivor outputs. Edge Board / Model-vs-KEI (#70) untouched.

## Method

1. Measure foundation (`v1`) demo outputs vs recent NFL reality (2022–2024 shapes).
2. Centralize knobs in `calibration.py` with documented sources.
3. Adjust priors / usage allocation / scoring; re-run identical seed demos.
4. Add sanity-bound tests for helpers + BUF@KC / season totals.

Artifacts:

- Baseline: `data/ops/nfl-season-engine-calibration-baseline/`
- After: `data/ops/nfl-season-engine-calibration-after/`
- Both: `--demo --n-sims 40 --game-reps 300 --sample-game BUF@KC --seed 2026`

## What changed (transparent)

| Area | Before (v1) | After (cal-v1) | Why |
| --- | --- | --- | --- |
| League PPG / HFA / score SD | 22.5 / +1.35 / 9.5 | **21.8 / +1.05 / 9.8** | Align with recent NFL + `nfl_handicapping_framework` |
| Plays / pass rate | 64 / 0.575 | **63 / 0.58** | Recent offense shape |
| Strength evolution | update 0.04, noise 0.012 | **0.025 / 0.010**, clamp 0.70–1.35 | Less mid-season win explosion |
| Demo strengths | hash jitter + mild bumps | **EPA-style tier bumps** (KC/BUF/PHI… vs CAR/TEN) | Realistic win ordering |
| Usage shares | renormalize to 100% | **Absolute shares + residual "other"** | Fix sparse-roster WR1/RB1 inflation |
| INT rate | 0.022 | **0.018** (elite 0.015) | Recent starter INT% |
| Pass / rush / rec TD rates | 0.046 / 0.038 / 0.07 | **0.041 / 0.027 / 0.055** | Season TD leaders in band |
| Efficiency CVs | flat 0.20 | **0.22 / 0.24 / 0.23** | Match box-score sim; useful p10–p90 |
| DB efficiency | defaults only | **baselines when present**, else league priors | Honest; no invented grades |

Four-layer architecture unchanged: `team_strength` → `game_script` → `player_usage` → `production`.

## Before / after metrics (demo, seed 2026)

### Game script — BUF @ KC

| Metric | Before | After |
| --- | --- | --- |
| home_win_prob | 0.550 | 0.533 |
| expected_total | **47.64** | **46.56** |
| pace_plays | 65.2 | 63.6 |

### Player game boxes (point estimates)

| Player | Stat | Before | After | Reality check |
| --- | --- | --- | --- | --- |
| Mahomes | pass yds / TD / INT | 267 / 1.71 / **0.85** | 247 / 1.52 / **0.57** | INT fixed; yards still QB1 band |
| Allen | pass yds / TD / INT / rush | 243 / 1.52 / 0.80 / 19 | 229 / 1.43 / 0.61 / **21** | Cleaner INT; rush still light vs career |
| Cook | rush / rTD / rec / recy | **102** / 0.83 / 4.5 / 50 | **59** / 0.39 / 2.6 / 19 | RB1 mean now realistic |
| Rice | recy / rec / rTD | **102** / **8.9** / 0.63 | **56** / **5.3** / 0.32 | WR1 mean now realistic |

Mahomes pass yards p10–p90 width: ~148 → ~149 (still useful).  
Rice rec yards width: 84 → 59 (tighter with lower mean; still actionable).

### Season totals (40 paths unless noted)

| Player | Stat | Before | After |
| --- | --- | --- | --- |
| Mahomes | pass yds / TD / INT | 4698 / 29.5 / **12.9** | ~4350 / ~25 / **~9.4** |
| Cook | rush yds / rTD | **1998** / **16.6** | **~1185** / **~7.7** |
| Rice | rec yds / rec / TD | (inflated ~1675 / 144) | **~1005 / ~88 / ~4.3** |

### Team win means

| | Before | After |
| --- | --- | --- |
| min–max mean wins | 4.5 – 11.4 | **5.7 – 10.7** |
| stdev of team means | 2.02 | **1.37** |
| top clubs | BAL/LAC/ATL (hash noise) | **BUF / DET / KC / PHI** |
| bottom | IND/TEN | **CAR / TEN / NYG** |

Win sum per path remains exactly 272.

## Remaining major biases / weak spots

1. **Win-mean compression** vs Vegas-style extremes (~3–14): demo round-robin + no injury model + analytic Layer 2 still pulls clubs toward ~6–11. DB EPA priors + real schedule should widen this.
2. **Allen rush volume** still light vs historical (~35–40 rush yds/game); needs role-specific rush priors / designed-run modeling (out of scope).
3. **INT model** still attempt-rate Poisson only — no pressure / down-distance.
4. **Layer 2** still analytic (not hooked into `simulate_nfl_game` replicate margins).
5. **DB baseline wiring** is best-effort; when `nfl_player_projection_baselines` is empty we document league-prior fallback (no fake player grades).
6. **No injury / availability shocks** inside season paths (explicitly deferred).

## Tests

`services/model-service/tests/test_nfl_season_engine.py`  
`services/model-service/tests/test_nfl_season_engine_calibration.py`

```bash
cd services/model-service && python3 -m pytest tests/test_nfl_season_engine*.py -q
# 11 passed
```

## Railway

Model-service routes `/nfl/season-engine/*` pick up `DEFAULT_SEASON_ENGINE_VERSION` and calibrated modules. Deploy the `kosedge` Railway service after merge if live HTTP queries should serve `v1.1-calibrated`.
