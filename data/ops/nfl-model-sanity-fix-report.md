# NFL Model Sanity Fix Report

**Date:** 2026-07-30  
**Branch:** `nfl-second-order-edge`  
**Symptom (example, not a special-case):** DAL @ NYG — market NYG +2.6 / DAL −152, model `spread_home` −3.07, `home_win_prob` 0.59, spread+ML **PLAY**.

## Root cause

Not HFA alone and not a single-game bug.

1. **Framework EPA alone favors Dallas.** Reconstructing offense/defense indices from the Week-1 matchup pack yields ~`spread_home` **+1.06** after 0.30 market blend (Cowboys slight favorite). Published line was Giants −3.07 — a ~4-point swing past the framework.

2. **Validated supervised blend unlocked on a not-yet-played season.** `detect_real_rolling_features()` only checked `COUNT(DISTINCT off_epa_per_play_5g) > 1`. Preseason hydration / carry-forward can put **week-varying** EPA into the 2026 week grid before any REG game is scored. That returned `True` for both clubs and unlocked `VALIDATED_BLENDING_WEIGHTS` (**85% supervised spread**, ±14 pt trust region). Conservative path is 30% / ±7.

3. **Slate pattern matched the failure mode.** Across 167 fair-lines: 24 side flips vs market; home dogs pulled ~1.8 pts toward home; big favorites compressed. Classic “high-trust supervised on OOD early-season features.”

4. **Secondary issues addressed**
   - Team strength priors looked up by full name while rolling table keys are abbreviations → silent fallback to weaker context indices.
   - Early-season market blend stayed at 0.30 even in Week 1.
   - PLAY tags could fire on market-side disagreements (Giants PLAY as favorite while market has them as dogs).

## Fixes shipped

| Change | File | Effect |
| --- | --- | --- |
| Real-features gate requires ≥3 **scored REG** games (weeks 1–18) **and** EPA variance | `nfl_supervised_retrain.py` | Blocks validated weights until in-sample season |
| Prior lookup prefers `home_abbr` / `away_abbr` | `tasks.py` | EPA priors actually apply |
| Early-season market blend boost (W1 +0.25 → ~0.55) | `nfl_simulator.py` | Anchors thin weeks to consensus |
| PLAY blocked on market side disagreement (≥1.5 pts opposite favorite) | `nfl_side_total_publish_policy.py` + fair-lines route | No stake tags on flip failures |

## Validation example (DAL @ NYG)

| | Market | Before (published) | Framework-only recon | After (expected) |
| --- | --- | --- | --- | --- |
| Home spread | +2.6 | **−3.07** | ~+1.1 | Cowboys side of market / no PLAY on flip |
| Home win prob | ~0.42 (no-vig) | **0.59** | ~0.47 | Near market after conservative blend |
| Spread PLAY | — | **PLAY** | — | **PASS** (`market_side_disagreement` until line sane) |

Exact post-deploy numbers require Railway re-sim (`run-nfl-simulations`).

## Residual risks

- Supervised model can still pull within the conservative trust region; Week 1–4 market boost mitigates.
- Totals remain sides-only; props research-only.
- Re-enable validated weights only after ≥3 scored REG games per team (automatic).

## Deploy / ops

1. Deploy model-service (`bash scripts/deploy-railway-model-service.sh`).
2. Trigger full NFL sim refresh / wait for 3am cycle.
3. Re-check fair-lines: DAL@NYG side agreement + PLAY tags; slate flip count.
