# VERDICT_ENG — t4910u bounded diagnostic score 70

**Eng self-label: CONDITIONAL_DIAG**

Not CERT. Not SCORE_SEALED as a certification. Not E1. Not PASS. Alex / CoS grade is separate.

## Why CONDITIONAL_DIAG (eng)

Holds:

- ASSUMPTIONS (including naive W-L formula) written **before** first SCORE_RESULTS write. Formula not changed after.
- All **70** complete games attempted. **70/70 SCORED**. 0 FAILED. 0 ties.
- Exclusions visible and not filled: W2 ineligible CHI_TB / MIA_LAC; W6 bye partials DET_NO / MIA_ATL / SF_WAS / NYG_DEN.
- rest BIND_PACKET_ONLY. Packet ET rest consumed as IF inputs. W8 UTC helper not called. Tip stayed **6ca03716**. Thu games kept packet rest=4.0 (UTC contrast 7.0 unused).
- IF loaded from 6ca03716 worktree. Simulator rehash **52d9e909 MATCH**. Framework **a0051cc4 MATCH**. market_blend=0 on all 70.
- Seed formula bound: `201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)`. simulations=4000. Tie margin==0 → away.
- Metrics use ACCEPT names: forecast margin/spread/total/wp vs realized; straight-up outcome accuracy (NOT ATS-vs-0); Brier/log-loss exploratory N=70; MAE/RMSE; compression with forecast-mean SD vs realized SD; sealed-sim p10–p90 coverage.
- No CLV. 2017 odds not consumed. 0 Odds credits. 2024–25 untouched. No math change.

Does not hold for SCORE_SEALED / CERT (eng view):

- Box EXEC_FREEZE / OWNER_ACCEPT sha8 remount unmatched (expected 5ecdef1c / 1102720e; observed 8ef7a834 / d3acd43d). Bind text followed; originals not mounted.
- EPA/success inputs remain RETRO_FIT / DEV_RESEARCH (A1).
- N=70 is exploratory. Coverage and Brier are not a certification sample.
- IF SU 0.4714 does not beat pick'em 0.5000 or naive W-L 0.5000. MAE does not beat the labeled baselines. That is a diagnostic result, not a defect to “fix” in this filing.

## Headline numbers (not edge)

| | IF | naive W-L | pick'em / 45.3 |
|---|---|---|---|
| SU (decided 70, ties 0) | 0.4714 | 0.5000 | 0.5000 |
| MAE margin | 10.745 | — | 10.486 (margin=0) |
| MAE total | 11.963 | — | 11.820 (45.3) |
| Brier | 0.2584 | 0.3048 | 0.2500 |
| sd forecast means / sd realized | 2.976 / 13.662 | | |
| coverage margin / total p10–p90 | 0.800 / 0.743 | nominal 0.80 | |

Forecast means are compressed vs outcomes (as expected). mean IF sigma ≈ 10.0 is the per-game noise term, not a claim that SDs should match.

## Not claimed

CERT · SCORE_SEALED-as-cert · E1 · market beat · CLV · ATS · PLAY / LEAN · FREE_PUBLIC · merge.

NFL NO-GO · CERT=0
