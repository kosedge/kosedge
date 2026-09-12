# Evidence lock — PR #543 supersedes PR #542

**Date:** 2026-09-12  
**Kill switch:** ON. No PLAY. No public CFB. No Line Curve.  
**This note:** evidence hierarchy only. It does not copy parquet, densify
closes, spend Odds API credits, recalibrate coefficients, unseal 2025,
or change QB / close / gate semantics.

## Authoritative result

**PR #543** is the current recovery **and** frozen 1.40 scoring result.

Environment: Mac private worker (`usePrivateWorker=true`).  
Artifact read directly, not copied into git:

`/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet`

Companion scoring report: `data/ops/cfb-frozen-140-scoring-20260912.md`

## Superseded result

**PR #542** is **not** current. It is cloud-VM environment evidence.

That run reported `This VM: HD unmounted`, `LAKE_NOT_MOUNTED`, and
Train-0 = 0. That is the mount failure later solved on the Mac worker.
It is not a missing-data regression and it does not reopen recovery.

Do not send Line Curve, warehouse-spine, or later agents backward onto
#542. Two screenshots from two compute environments are not two facts
about the lake. The Mac result is the relevant one because that is
where the authoritative lake lives.

## Verified recovery funnel (2022, lake)

| Step | n |
| --- | ---: |
| raw lake snapshots | 28,322 |
| valid pregame lake closes | 717 |
| identity-matched | 713 |
| FBS/FBS | 713 |
| actual available | 713 |
| Train-0 W1–14 close+actual from the lake | 712 |
| leakage failures | 0 |

Gate ≥700 **PASSED**.

## Frozen 1.40 scoring — already completed on #543

Decision: **RECALIBRATION JUSTIFIED**

Coefficients were scored, not moved. This assignment does not retune
`MATCHUP_RESPONSE=1.40`.

| Split | n | Gate |
| --- | ---: | --- |
| Train-0 2022 W1–14 | 712 | ≥700 PASS |
| Val-0 2023 W1–14 | 710 | — |
| Train-1 2022+2023 | 1422 | — |
| Val-1 2024 W1–14 | 717 | ≥700 PASS |

Val-1 mean model total **63.8** vs close **52.5** vs actual **53.7**.
Total vs close bias **+11.34**. High-tail (predicted ≥68) n=217, bias
**+17.79**. ATS/ROI cannot override that MAE/bias failure.

## Forbidden

- Copy, recreate, or densify the parquet into the repo
- Spend The Odds API historical credits
- Reopen #542 as though Train-0 is still 0
- Recalibrate coefficients, QB weights, class multipliers, or PPG
- Change QB contract, close semantics, or the n≥700 gate
- Unseal 2025
- Publish CFB or emit PLAY

Scoring is complete. Stop here.
