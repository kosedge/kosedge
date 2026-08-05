# CFB Historical Closing-Line Calibration (v0.8.1)

**Branch:** `feat/cfb-historical-calibration` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.8.1-hist-cal`  
**Date:** 2026-08-05  
**Artifacts:** `data/ops/cfb-historical-calibration-20260805/`  
**Script:** `scripts/cfb/run_historical_calibration.py`

## Goal

Calibrate the hierarchical CFB engine against **actual closing spreads/totals and final scores**, not just internal coherence — without ripping out roster / QB / efficiency layers.

## Data (credits-safe)

| Source | Role |
| --- | --- |
| SportsDataverse `espn_cfb_betting` | Resolved closing-ish spreads + totals |
| SportsDataverse `espn_cfb_team_box` | Team identities (abbr / name) |
| SportsDataverse `espn_cfb_linescores` | Final scores |
| SportsDataverse `cfb_ratings` (prior year) | adj EPA → 0–100 efficiency proxy |

**Not used:** Odds API historical densify (credit burn). CFBD requires a key (unavailable in this pass).

## Reconstruction limits (honest)

The live 2026 hierarchy uses prior-year SP+ **plus** ESPN roster/QB/units. For seasons 2022–2025 we **do not** have packaged historical roster/QB snapshots. Proxy:

1. Prior-year `cfb_ratings` adj EPA → `off_eff` / `def_eff`
2. League-average roster / QB / position groups
3. Curated HFA buckets (2026 venue priors)
4. Coaching assumed all-returning

This grades efficiency weighting, matchup response, HFA, PPG, and early-season soften — **not** a perfect counterfactual of “what v0.8 would have projected with that year’s portal class.”

## Before → after (comparable: 2023–2024)

Primary holdout used for knob decisions. Sample grew after team-map expansion (`n` 1322 → 1572); directionally the same slate family.

| Metric | Before (v0.8) | After (v0.8.1) |
| --- | ---: | ---: |
| n games | 1322 | 1572 |
| Spread vs close MAE | 8.43 | **8.27** |
| Spread vs close bias | +1.09 | +1.26 |
| Total vs close bias | **+3.23** | **−0.48** |
| Total vs close MAE | 6.20 | 6.21 |
| Margin vs actual MAE | 14.73 | **14.45** |
| ATS hit (model side ≥0.5 pt) | 51.5% | **52.0%** |
| OU hit | 52.6% | 50.7% |
| ML hit | 63.8% | 63.4% |
| Brier (home WP) | 0.219 | 0.220 |
| Home-favorite spread bias | +7.30 | **+6.82** |
| Home-dog spread bias | −8.81 | **−7.62** |
| Early (W1–4) spread MAE | 9.61 | **9.18** |
| Late (W5+) spread MAE | 7.92 | 7.88 |

## Full sample after (2022–2025)

| Metric | After |
| --- | ---: |
| n | 2393 |
| Spread vs close MAE / RMSE | 8.25 / 10.60 |
| Total vs close bias / MAE | −0.54 / 5.96 |
| ATS / OU / ML | 51.6% / 50.9% / 64.2% |
| Brier | 0.219 |

## Knobs changed (measured)

| Knob | Before | After | Why |
| --- | ---: | ---: | --- |
| `ENGINE_VERSION` | `v0.8-efficiency` | `v0.8.1-hist-cal` | Version bump |
| `LEAGUE_TEAM_PPG` | 27.5 | **25.9** | Totals +3.2 vs close |
| `HFA_BASELINE_POINTS` + buckets | 2.0 / elite 3.4 | **1.7 / elite 3.1** | Home dogs overrated vs close |
| `MATCHUP_RESPONSE` | 1.22 | **1.40** | Spreads compressed vs close |
| `MATCHUP_RATIO_CLAMP` | (0.55, 1.38) | **(0.52, 1.45)** | Allow clearer favorites after decompress |
| `WEIGHT_OFF_EFF` / `WEIGHT_DEF_EFF` | 0.28 / 0.30 | **0.34 / 0.36** | Efficiency must drive when identity noisy |
| Roster/QB offense weights | 0.24 / 0.26 | 0.22 / 0.24 | Still first-class (≥0.20) |
| `EFF_*_INDEX_BLEND` | 0.08 | **0.12** | Mild post-compose efficiency pull |
| Early `SEPARATION_SOFTEN` W1 | 0.82 | **0.90** | Early under-rated favorites |
| `WIN_PROB_MARGIN_SD` | 14.5 | 15.2 | Align WP with wider spreads |

**Preserved:** roster / QB / efficiency / HFA / coaching / player-hooks architecture; Edge Board markets-only; UI routes.

## Remaining systematic biases

1. **Favorite compression** — home favorites still ~+7 pts too soft vs close; home dogs ~−8 too bullish. League-avg identity reconstruction understates talent gaps vs market.
2. **Early season** — still worse MAE than late (~9.2 vs ~7.9); portal/QB identity missing in hist proxy.
3. **Coverage gaps** — some FBS codes absent from 2026 priors remain unmapped / FCS skipped.
4. **Not CLV / KEI** — ATS ~52% with 0.5-pt edge filter is not a betting product claim.
5. **Efficiency proxy ≠ SP+** — `cfb_ratings` adj EPA, not Bill Connelly SP+.

## How to reproduce

```bash
PYTHONPATH=services/model-service \
  python3 scripts/cfb/run_historical_calibration.py --phase after --seasons 2022,2023,2024,2025
```

## Tests

- Driver non-regression (blue-blood vs G5, HFA ordering, early margin_sd, player hooks)
- `test_hist_cal_priors_bounds` — PPG / HFA / matchup / efficiency weight clamps
- `test_hist_cal_proxy_reconstruction_keeps_drivers`

## UI

`/pro/cfb/model` and `/pro/cfb/project-game` unchanged in structure; live `engine_version` from status shows `v0.8.1-hist-cal`. Status exposes `historical_calibration` ops pointer.
