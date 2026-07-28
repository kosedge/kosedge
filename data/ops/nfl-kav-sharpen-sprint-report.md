# NFL KAV Sharpen Sprint Report

Generated: 2026-07-28  
Branch: `nfl-kav-sharpen`  
Commit: `d63c6ed1` (+ follow-ups)

## 1. KAV (owned efficiency)

**Definition:** Kos Edge Adjusted Value — iterative opponent-adjusted EPA/play from owned nflverse PBP. Not Football Outsiders / FTN DVOA. Spec: `docs/NFL_KAV.md`.

| Item | Status |
| --- | --- |
| Migration | `infra/db/041_nfl_kav_efficiency.sql` |
| Materializer | `--materialize-kav` / `data_platform_nfl.kav` |
| Seasons materialized | **2013–2025** (13 seasons, ~7k team-games) |
| Matchup attach (week−1 lag) | **3140 / 3834** rows (week 1 null by design) |
| Handicapping | `kav_efficiency` factor (framework v3) |
| Supervised | schema v3 FEATURE_KEYS |
| External DVOA | placeholder only, disabled |

2024 W18 net KAV leaders (sanity): BAL, DET, BUF, PHI, GB.

## 2. Odds grading (DB-first, no API pull)

Artifact: `data/ops/nfl-odds-open-close-grading.json`

| Metric | Market close | Model |
| --- | --- | --- |
| Spread MAE | 9.778 | **9.613** |
| Total MAE | 10.300 | **10.123** |
| ML Brier | 0.224 | **0.200** |
| ATS hit rate | — | 0.493 |
| CLV spread avg / +rate | — | **+2.02 / 66.0%** (n=159 owned OC) |
| CLV total avg / +rate | — | **+1.29 / 63.3%** (n=117) |

Coverage: 1693 graded games 2020–2025; **724** owned open/close games in `odds_snapshots`; owned OC dense in 2024–25; earlier seasons use nflverse closes.

## 3. Calibration before → after

Artifact: `data/ops/nfl-calibration-retune-owned-20260728.json`  
Method: invert stored projection blend → sweep weights + fit totals calibrator on 2023–24; holdout 2025 (n=269).

| | Blend S/T | Holdout spread MAE | Holdout total MAE |
| --- | --- | --- | --- |
| **Before (current defaults)** | 0.30 / 0.30 | 8.547 | **9.547** |
| After (tune-best + affine cal) | 0.25 / 0.35 | 8.529 | 9.763 |
| Delta | — | −0.018 | **+0.216** |

**Decision:** do **not** promote new blend/cal defaults. Holdout joint gate failed (totals regress). Keep `NFL_MARKET_BLEND_* = 0.30`. Totals calibrator remains the live adaptive path in `nfl_totals_calibration.py`.

## 4. Tests

- `tests/test_kav.py` — 6 passed (math, SOS, leakage)
- `test_nfl_handicapping_framework.py` + `test_nfl_matchup_features.py` — 7 passed (incl. KAV factor)

## 5. DB note

Primary warehouse for this sprint: `kosedge_nfl_restore` (restored DR dump + KAV). Slim `kosedge` DB remains empty of NFL core tables — ops should point `DATABASE_URL` at the restored warehouse or promote restore → `kosedge`.

## 6. Remaining gaps

1. Promote restore DB (or re-ingest) so default `kosedge` has schedules/PBP/odds/KAV.
2. Re-sim 2025 slate **with KAV wired** for true before→after vs pre-KAV projections (current grading uses existing projections).
3. Supervised retrain schema v3 on KAV features + chronological holdout.
4. Densify owned open/close for 2020–2023 mainlines (DB-first gap pull only).
5. Special-teams KAV unit (deferred; pass/run EPA only in v1).
