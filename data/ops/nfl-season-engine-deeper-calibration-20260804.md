# NFL Season Engine — Deeper Calibration & Preseason Tuning (v1.11)

**Date:** 2026-08-04  
**Branch:** `feat/nfl-season-engine-deeper-calibration` → `deploy-vercel`  
**Base:** `nfl-season-engine-v1.10-survivor-planner` (PR #91)  
**Engine version after:** `nfl-season-engine-v1.11-calibration`  
**Calibration tag:** `nfl-season-engine-cal-v2`  
**Scope:** Measured knobs only — no new major features, Survivor Planner intact.

## Method

1. Measure v1.10 packaged-real biases (win width, PPG/totals, role means, RZ TD shape).
2. Tune `calibration.py` / role tables / RZ finish / strength evolution / early-season multipliers.
3. Fix real-depth QB1 attempt starvation (backup snap priors over-started QB2/QB3).
4. Re-measure with identical seeds; document before/after.

Artifacts:

- `data/ops/nfl-season-engine-calibration-v2-20260804/baseline/`
- `data/ops/nfl-season-engine-calibration-v2-20260804/after/`

## What changed (transparent)

| Area | Before (v1.10 / cal-v1) | After (v1.11 / cal-v2) | Why |
| --- | --- | --- | --- |
| Matchup response | 0.96 hard-coded | **`MATCHUP_RESPONSE=1.12`** (week-aware) | Widen season win separation |
| Win-prob margin SD | 13.8 | **12.6** mid-season; W1–W4 inflate | Sharper favorites mid-year; honest early |
| Strength evolution | noise 0.010 / revert 0.016 | **0.014 / 0.011**, update 0.028 | Less win-mean compression |
| Early-season (W1–W4) | none in season engine | Score/margin SD ↑, separation soften, share vol ↑, Dirichlet ↓ | Roles settle; surface `early_season_uncertainty` |
| YPA / pass TD rate | 7.05 / 0.041 | **7.15 / 0.043** | Real-depth QB1 yards/TDs were light |
| TE YPR / target / RZ tgt | 10.6 / 0.14 / 0.18–0.24 | **10.3 / 0.125 / 0.16–0.22** | TE1 was matching WR1 yards |
| RZ finish (pass/rush/rec) | 0.18/0.32 · 0.12/0.36 · 0.20/0.34 | **0.20/0.35 · 0.12/0.37 · 0.19/0.32** | Elite pass TD lift; mild rec fade |
| QB starter prior | categorical on snap×1/depth | **`QB1_START_RATE=0.965`** | Real depth QB2/3 snap priors starved QB1 |

Architecture unchanged: strength → script → usage (+ RZ) → production. Survivor planner + injury paths unchanged.

## Before / after (packaged real 2026, seed 2026)

### Season win distribution

| Metric | Before (v1.10, n=8) | After (v1.11, n=12) |
| --- | --- | --- |
| win_mean min–max | 5.25 – 11.63 | **3.75 – 12.17** |
| win_mean stdev | 1.56 | **2.02** |
| win_mean spread | 6.38 | **8.42** |
| top clubs | DET / DEN / BAL | **KC / DET / PHI / SF / BAL** |
| bottom clubs | LV…NYG (~5.3) | **NYG / CAR / NE (~3.8–5.0)** |

Much closer to recent NFL / Vegas-style width; extremes (~2–14) still a soft spot at low sim counts.

### BUF @ KC (week 1) + SF @ LA sanity

| Metric | Before | After |
| --- | --- | --- |
| BUF@KC expected total | ~46.1 | **~45–46** |
| Mahomes pass yds / TD / INT | demo ~253 / 1.42 / 0.53; real-depth starved ~180 | **real ~244 / 1.51 / 0.61** (attempts ~38) |
| Cook rush yds | ~51 | **~42** (RB1 band; no inflation) |
| Rice rec yds / rec | ~67 / 6.1 | **~54 / 5.1** |
| Kelce rec yds | ~46–50 | **~49** (WR1 ≥ TE1 yards) |
| SF@LA total / home WP | ~45.1 / 0.45 | **~44.0 / 0.47** |

Week 1 vs Week 10: early-season diagnostics active on W1 (`score_noise_sd≈11.6`, softened separation); W10 inactive with sharper home WP.

### Season player totals (illustrative)

| Player | Stat | Before | After |
| --- | --- | --- | --- |
| Mahomes | pass yds / TD / INT | ~4515 / **22.4** / 10.8 | **~4330 / ~25 / ~11** |
| Cook | rush yds | ~1100 | **~860–1100** (path noise; game mean OK) |
| Rice | rec yds / rec / TD | ~1098 / **99** / 6.8 | **~880 / ~79 / ~5** (less WR inflation) |

## Diagnostics

- Game-boxes (`include_diagnostics=true`): `diagnostics.early_season_uncertainty`
- Season sim: `diagnostics.early_season_uncertainty.by_week` + `week_5_plus`

## Remaining soft spots

1. **Win totals** still compressed vs market extremes (~3–14); need stronger EPA priors / less analytic Layer-2 smoothing for Vegas-like tails.
2. **Allen designed rush** still light vs career (~35+ rush yds/g) — role-specific QB rush prior, not just snap share.
3. **TE receptions** can still sit near WR1 on TE-heavy clubs (Kelce); yards ordering improved.
4. **INT model** still attempt-rate Poisson only.
5. **Camp depth churn** — early-season vol helps but does not replace real depth updates.
6. Season-total RB1 yards path-noisey at low `n_sims`; trust game-level means + higher sim counts for ops.

## Tests

```bash
cd services/model-service && python3 -m pytest tests/test_nfl_season_engine*.py -q
# 96+ passed (includes new early-season + real-depth QB1 attempt guards)
```

## Railway / web

Model-service routes pick up `DEFAULT_SEASON_ENGINE_VERSION=nfl-season-engine-v1.11-calibration` after deploy. Survivor `/survivor` + `/survivor/plan` unchanged in contract shape; diagnostics gain `early_season_uncertainty` only.
