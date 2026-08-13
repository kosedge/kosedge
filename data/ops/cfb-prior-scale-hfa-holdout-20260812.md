# CFB Prior Scale + HFA Holdout Calibration

**Date:** 2026-08-12  
**Branch:** `feat/cfb-prior-scale-hfa-holdout` → `deploy-vercel`  
**Depends on:** #218 walk-forward (measurement locked)  
**Doctrine:** Fix magnitude on holdout. Do not chase in-sample ATS. No EPA in this fair. **No KEI. No Edge tags.**

Script: `python scripts/cfb/run_prior_scale_hfa_holdout.py`  
Pack: `services/model-service/src/services/cfb_season_engine/data/cfb_prior_scale_hfa.json`  
Full numbers (HD): `/Volumes/KosEdgeData/clean/cfb/historical/walkforward/prior_scale_hfa_holdout.json`  
Repo summary: `data/ops/cfb-prior-scale-hfa-holdout-20260812-summary.json`

## Model fair (this pass only)

```
fair_spread_home = -HFA - scale * (prior_home - prior_away)
```

- `prior_*` = program prior mean (pts vs avg FBS), seasons **< Y** only
- Negative = home favored (same as lake / project-game)
- Neutral site → HFA = 0
- **No** Week 2–4 EPA blend
- **No** final-season ratings
- One global `(scale, HFA)` — not per-conference, not per-week

**Close:** last owned lake snap strictly before kickoff. **Not a true lock.**

**Baseline:** `scale=1`, `HFA=1.7` (engine `HFA_BASELINE_POINTS`). Unscaled prior.

## Split (no peek)

| | Years | Fit weeks | Eligible (prior + close) |
| --- | --- | --- | ---: |
| **Train** | 2020–2023 | 0–4 | **774** |
| **Holdout** | 2024–2025 | 0–4 | **475** |

2020 closes were kept (71 train rows dropped for missing close; n still healthy). Fit is grid MAE on **train only**. Holdout is eval-only.

Excluded (not imputed): train identity/FCS 331, no prior 8, no close 71. Holdout identity/FCS 245, no prior 7, no close 0.

## Chosen constants

| | |
| --- | --- |
| **scale** | **2.75** |
| **HFA** | **3.8** pts (band [0, 4]; not at the cap) |
| Method | grid MAE, scale ∈ (0.25, 5], HFA ∈ [0, 4] |
| Adopt | **yes** — holdout W0–4 MAE improved **2.70** pts (margin 0.50) |
| `used_in_spread` | **false** — research pack only. Not wired into project-game / KEI / Edge Board. |
| `epa_in_fair` | **false** |

## Primary — holdout (2024–2025)

| Window | n | Baseline MAE | Calibrated MAE | Δ MAE | Bias (mean err) base → cal | ATS vs close | ATS CI |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| **W0–4** | **475** | 9.60 | **6.90** | **−2.70** | +4.40 → **+0.32** | 48.0% | 43.3–52.6% |
| W0–1 | 175 | 8.06 | **6.93** | −1.13 | +3.94 → +0.84 | 45.1% | 37.6–52.8% |

Holdout n is not thin. Magnitude improved by a clear margin. Bias (we were systematically too small vs the close) is mostly gone.

ATS is still a coin flip — slightly **worse** point estimate than baseline (49.8% → 48.0% on W0–4). CIs cover 50%. That is OK: this pass fixes **scale**, not edge.

CLV stub (fair vs close; last owned snap, not lock): calibrated W0–4 mean **−0.15**, positive **33.2%**. Not a “market follows us” story.

## Train (2020–2023) — overfit check, reported second

| Window | n | Baseline MAE | Calibrated MAE | Δ MAE | ATS vs close |
| --- | ---: | ---: | ---: | ---: | ---: |
| W0–4 | 774 | 9.62 | 6.99 | −2.63 | 47.1% |
| W0–1 | 264 | 8.56 | 7.46 | −1.11 | 44.6% |

Train and holdout MAE drops are almost the same size. Not an in-sample-only fit.

## Example — 2024 W1 UGA vs Clemson (neutral, **holdout**)

ESPN `401628323`. Close = last owned DK snap **2024-08-27 16:54Z** for kickoff **2024-08-31 16:00Z**. Result UGA 34–3.

| | Fair (home) | vs close −13.5 |
| --- | ---: | ---: |
| Unscaled (scale=1, HFA=0 neutral) | **−5.04** | +8.46 short |
| Calibrated (scale=2.75, HFA=0) | **−13.86** | **−0.36** |

Elite favorite moved to market magnitude. Did **not** flip to a dog. Neutral correctly dropped HFA.

## Plain English

**Yes — magnitude improved on holdout.** Unscaled program prior was right-side, wrong-size (UGA −5 vs market −13.5). A single scale of 2.75 plus HFA 3.8 (0 on neutrals), fit on 2020–23 only, cut holdout Week 0–4 MAE from 9.6 to 6.9 and pulled bias from +4.4 toward zero.

**ATS is still a coin flip.** Do not publish KEI, PLAY, or Edge Board CFB tags from this. CFB product stays markets-only until a future bar is actually cleared.

Constants are adopted as a **research pack** (`used_in_spread: false`). They are not applied to the live project-game spread in this PR.

## Leakage / honesty

- Prior for season Y uses only seasons < Y (#216 / #218 contract)
- No EPA in this fair
- Close = last owned pre-kickoff snap (not lock)
- Did not retune on holdout
- Did not ship KEI or change Edge Board
- Optional v1.1 conference HFA was **not** added; global pair was stable

## After this

Holdout scale helped. Optional next: a second walk-forward **note** using this calibrated fair (still research-only). Do not put it on the board. Roster-year priors remain the bigger feature gap if we want anything beyond magnitude.
