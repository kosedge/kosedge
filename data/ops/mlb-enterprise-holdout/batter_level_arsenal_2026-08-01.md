# MLB batter-level lineup-ID arsenal (2026-08-01)

**Window:** densify `2026-05-20 → 2026-07-17` (no Odds densify)  
**Task:** `b52bf4c4-bd7c-42d7-ae80-3bbfa5f41c3c` (`run_mlb_pitch_matchup_ablation` M0/M1/M1b)  
**PR:** [#63](https://github.com/kosedge/kosedge/pull/63) (wiring, defaults OFF)  
**Stack held:** S0 (HFA 1.025, matchup ON, wind-dir ON, era_whip; timing off; park-rel totals off; stuff off)  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10`; stake OFF  
**Flags (defaults):** `MLB_PITCH_MATCHUP_ENABLED=false`, `MLB_PITCH_MATCHUP_BATTER_LEVEL=false`  
**Artifact:** `batter_level_arsenal_2026-08-01.json`  
**Railway:** deployed (`scripts/deploy-railway-model-service.sh --wait`); API healthy; force-resim `max_games=1200` (no 400-cap gap; 628/628/628)

## What was built

1. Per-batter as-of contact-by-pitch-family index: `batter_contact_asof_index.json` (MLBAM batter id)
2. `get_batter_contact_as_of` with same-day leakage cutoff (as-of exclusive of game day)
3. `blend_lineup_batter_contact` — slot-weighted blend; requires enough batters/pitches
4. `resolve_batter_family_for_matchup` — batter-level when flag on + lineup IDs; else team-family
5. Lineup features include `person.id` for densify/live cards
6. Ablation arm **M1b** in `run_mlb_pitch_matchup_ablation` (M0 / M1 / M1b)
7. Unit tests: `tests/test_mlb_batter_level_arsenal.py` — **12** arsenal+batter tests passed locally

## Intersection-n (n = 476)

| Config | Inter ML CLV | Inter RL CLV | Inter Tot CLV | WF Brier | MAE | Leak | Sim |
|--------|-------------:|-------------:|--------------:|---------:|----:|-----:|----:|
| M0 off | +0.00383 | +0.051 | +0.004 | 0.25047 | 3.483 | **0** | 628 |
| M1 / M1t team-family | +0.00392 | **0.000** | +0.002 | 0.24997 | 3.490 | **0** | 628 |
| M1b batter-level | **+0.00364** | +0.013 | +0.002 | 0.25131 | 3.482 | **0** | 628 |

M1b − M0 ML = **−0.00019** (worse). Full-n ML CLV matches intersection (n_ml=476 / 628 games). ECE: M0 0.0233 · M1 0.0229 · M1b 0.0238.

## Gate check

| Gate | Target | Result |
|------|--------|--------|
| Leakage | 0 | **PASS** (0; repaired 0) |
| Intersection ML CLV | ≥ +0.010 | **FAIL** (+0.00364) |
| Stretch | ≥ +0.015 | **FAIL** |
| Beats M0 | yes | **FAIL** (−0.00019) |
| RL/total not torched | hold | **SOFT FAIL** (RL +0.051 → +0.013; total +0.004 → +0.002) |

## Decision

**Do not flip `MLB_PITCH_MATCHUP_ENABLED` or `MLB_PITCH_MATCHUP_BATTER_LEVEL`.** Production stays off.

Batter-level contact blend is honest (leak 0, full 628 sim, n=476 intersection) but **not subscription-grade**. Stop PA-mul research; next path is architecture (market-aware ML head) with unused holdout frozen.
