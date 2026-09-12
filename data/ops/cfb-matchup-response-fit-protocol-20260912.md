# CFB MATCHUP_RESPONSE recalibration — authorized coefficient-fit stage

**Date:** 2026-09-12  
**Depends on:** PR #543 (authoritative recovery + frozen 1.40 scoring)  
**Kill switch:** ON. No PLAY. No public CFB. Production `MATCHUP_RESPONSE` stays **1.40**.

This ticket does **not** mutate recovery. #542 cloud-VM n=0 remains superseded.

## Why this stage is authorized

#543 reconstructed `cfb-qb-feature-v1`, read the original 2022 lake, passed
Train-0 n=712 ≥ 700, and scored frozen 1.40.

Decision on that legal universe: **RECALIBRATION JUSTIFIED**.

- Val-1 n=717
- total vs close bias **+11.34**
- high-tail (predicted total ≥68) bias **+17.79**

B (wrong QB distribution) is no longer a live confounder. 1.40 has to
answer for itself. That does **not** authorize guessing 1.18.

## Isolated parameter

Fit **only** `MATCHUP_RESPONSE`. Early-season soften stays
`candidate * EARLY_SEASON_SEPARATION_SOFTEN[week]`.

Do not move PPG, QB weights, class multipliers, ratio clamps, close
semantics, leakage rules, or Layer B. Do not unseal 2025. Do not use
2026 in the loss.

## Grid (pre-registered)

Coarse: `0.70, 0.75, …, 1.50` step 0.05, plus **1.18** as an unprivileged
listed node.

Refine: ±0.04 around the Train-1 loss minimizer, step 0.01, skipping
already-scored nodes.

## Loss and decision

- **Rank on Train-1** with
  `total_vs_actual_MAE + 0.25*|total_vs_actual_bias| + 0.50*|frozen-1.40-tail vs actual bias|`
- **Decide on Val-1**
- Close is diagnostic. ATS/ROI cannot pass a failed MAE/bias gate.
- High-tail comparison uses the **frozen 1.40 ≥68 game set** so candidates
  are judged on the same inflated games, plus each candidate’s own tail n.

Val-1 materiality vs 1.40 (all required for EARNED):

1. total vs actual MAE improves by ≥1.0 or ≥8%
2. |total vs actual bias| shrinks ≥50% or lands inside ±4
3. frozen-1.40-tail vs actual bias improves ≥40% or |bias| < 8
4. margin vs actual MAE does not worsen by >0.75
5. mean |model spread| does not collapse below 50% of |close spread|
6. selected value is within 0.05 of a Train-1 top-3 and a Val-1 top-3

Labels:

- **COEFFICIENT CANDIDATE EARNED** — Val-1 actual gates + stability
- **BROADER MODEL RECALIBRATION REQUIRED** — exponent-only cannot fix
  location without killing spreads, or the needed response is ≤0.75 and
  still biased (PPG / QB index location)
- **INSUFFICIENT EVIDENCE** — n gates fail, or Train-1 vs Val-1 disagree
  by >0.15 without a clean Val-1 win

A candidate is **not** written into `priors.py` in this assignment.

## STOP

STOP before 2025. STOP before production. STOP before PLAY.
