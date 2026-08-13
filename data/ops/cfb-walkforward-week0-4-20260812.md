# CFB Week 0–4 Walk-Forward vs Lake Closes

**Date:** 2026-08-12  
**Branch:** `feat/cfb-walkforward-week0-4` → `deploy-vercel`  
**Depends on:** #217 (QB honesty) + #216 (efficiency + prior)  
**Doctrine:** Measure research fair vs market. Zero leakage. Thin samples flagged. **No KEI.**

Script: `python scripts/cfb/run_walkforward_week0_4.py`  
Numbers: `data/ops/cfb-walkforward-week0-4-20260812-summary.json`

## Model fair (this harness)

| Window | Weeks | Fair |
| --- | --- | --- |
| **w0_1** | 0–1 | Program prior only: `points = net_epa_adj × 28` from seasons **< Y**. Flat HFA **1.7** (engine baseline) unless `neutral`. |
| **w2_4** | 2–4 | `0.55 × prior + 0.45 × entering-week efficiency` (same EPA→points). Missing/cold-start efficiency → **incomplete**, not silent zero. |
| **w5_plus** | 5+ | `0.25 × prior + 0.75 × efficiency` (contrast only). |

`model_spread_home = −(home_strength − away_strength + HFA)` (negative = home favored).

**Not used:** 2026 roster/QB pack (would leak a future overlay into 2020–25). Final-season ratings for season Y. Post-game EPA. 2026 venue HFA buckets.

**Close:** last owned lake snap strictly before kickoff. **Not a true lock.** SDV fill when lake missing; fidelity on the row.

Efficiency leakage proof is `feature_week < game_week` (Phase A contract). Snapshot `available_at` is a bucket max and is often unusable (PBP↔ESPN id mismatch); those timestamps are ignored, not treated as future features.

## Headline — is the prior noise?

**Early-season research fair does not beat the close.** Keep it as a leakage-safe strength/uncertainty view. Do **not** publish KEI or board lines from it.

| Window | n with close | MAE | ATS vs close | 95% CI | Flag |
| --- | ---: | ---: | ---: | --- | --- |
| **Week 0–1** | **439** | 8.36 | **47.7%** | 43.0–52.5% | ok (n>50) |
| **Week 2–4** | **763** | **10.36** | 51.0% | 47.3–54.6% | ok |
| Week 5+ | 2,955 | 6.61 | 50.5% | 48.6–52.3% | contrast |
| Overall | 4,157 | 7.48 | 50.3% | 48.7–51.8% | |

ATS CIs all cover 50%. Week 0–1 point estimate is **below** 50%. Week 2–4 MAE is **worse** than prior-only (early EPA is noisy). Coin-flip vs close is the honest read.

CLV stub (sign of close moving toward the model from open): overall mean **+0.21** pts, positive only **33.5%** of the time. Not lock CLV. Not a “market follows us” story.

Mean error is **positive** (~+2 overall, **+4.1** in Week 0–1): we are systematically **less home/favorite** than the close (compressed program scale vs market).

## By season (no silent year drop)

| Season | Games | n close | unmatched close | MAE | ATS |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2020 | 571 | 420 | 59 | 7.74 | 48.6% |
| 2021 | 891 | 687 | 77 | 7.79 | 50.5% |
| 2022 | 900 | 711 | 62 | 7.63 | 53.6% |
| 2023 | 911 | 777 | 4 | 7.42 | 50.5% |
| 2024 | 965 | 776 | 0 | 7.20 | 48.8% |
| 2025 | 958 | 786 | 0 | 7.28 | 49.2% |

2020–22 have thinner lake coverage (unmatched kept). 2022 ATS 53.6% CI still includes 50% (49.8–57.3%).

Portal-era 2022+ (n=3,050): MAE 7.38, ATS 50.5%. Pre-2022 (n=1,107): MAE 7.77, ATS 49.8%. Not hidden; not a different sport.

Incomplete: 701 identity/FCS, 88 missing prior, 100 missing/cold efficiency. FCS not zeroed.

## Example — 2024 Week 1 UGA vs Clemson (neutral)

ESPN `401628323`. Close = last owned DK snap **2024-08-27 16:54Z** for kickoff **2024-08-31 16:00Z** (not lock).

| | |
| --- | --- |
| Result | UGA 34–3 (margin +31) |
| Open / close | −13.5 / −13.5 |
| Prior-only fair | **−5.04** (UGA − CLEM program, HFA 0) |
| Spread error | **+8.46** (we were 8.5 pts short of the close) |
| Model ATS pick | away / less home (`ats_hit=false`) — UGA covered easily |
| CLV stub | 0 (open = close) |

Program prior ranked UGA over Clemson but **far too close** vs a −13.5 market. That is the Week 0–1 failure mode: right side of “who’s better,” wrong magnitude vs close.

## Gaps

- Close ≠ lock when densify is sparse (this UGA–CLEM snap is four days early).
- Historical fair is **program-only**. 2026 QB/roster honesty is the live pack; it was not backtested here (no 2026 results yet).
- Week 2–4 blend weights are defaults, not holdout-tuned. They **hurt** MAE; do not retune in-sample on this same file.
- Snapshot `available_at` is not a trustworthy timestamp; week index is.
- 1.7 flat HFA is not team-venue HFA.

## Plain English

The research prior is a **reasonable ranking prior**, not a closing-line beater. Early-season ATS is a coin flip with a CI that includes 50%; MAE is 8+ points in Week 0–1. The Week 2–4 efficiency blend is currently **worse**, so do not promote it. **No KEI.** Next, if anything: holdout retune of scale/HFA/blend — or fix efficiency — **before** any board line.

```bash
python scripts/cfb/run_walkforward_week0_4.py
python scripts/cfb/run_walkforward_week0_4.py --seasons 2024,2025

cd services/model-service
DATABASE_URL=postgresql://test:test@localhost:5432/test \
  pytest tests/test_cfb_walkforward_week0_4.py tests/test_cfb_warehouse_leakage.py -q
```
