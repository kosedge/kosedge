# MATCHUP_RESPONSE coefficient sweep (v1 universe)

**Generated:** `2026-09-12T03:30:00Z`  
**Contract:** `cfb-qb-feature-v1`  
**Production MATCHUP_RESPONSE:** `1.40` (unchanged)  
**Sweep harness:** score-time overlay only. Early-season soften still applies.  
**Primary objective:** actual outcomes. Close is a benchmark, not the target.  
**Kill switch:** ON. 2025 sealed. 2026 not in the loss. No PLAY. No Line Curve.

## Decision

**INSUFFICIENT EVIDENCE**

- PR #543 remains the authoritative frozen-1.40 score (Train-0 n=712, Val-1 n=717, Val-1 total-vs-close bias +11.34, high-tail ≥68 close-bias +17.79).
- The coefficient-fit harness is implemented and unit-tested on this branch.
- The legal Odds-API lake (`/Volumes/KosEdgeData/clean/odds/cfb/snapshots-{2022,2023,2024}.parquet`) is **not mounted on this cloud VM**.
- Ryan’s MacBook Air private worker (`3c358d2d-51c7-5c49-9a19-6f9fbccd8be6`) is connected, idle, and is the machine that scored #543.
- This run cannot pin a Task/subagent onto that worker (`CreateAgent` is not in the tool catalog; Task `machine.type` only accepts `same_machine` | `new_cloud_vm`).
- No candidate was scored. No coefficient was guessed. No Vegas-clone fit was performed.

Production `priors.MATCHUP_RESPONSE` was **not** written. CFB remains dark. 2025 remains sealed.

## What is ready (do not re-litigate)

The fit stage is a one-command job on the Mac that already has the lake:

```bash
git fetch origin cursor/cfb-matchup-response-sweep-1bf8
git checkout cursor/cfb-matchup-response-sweep-1bf8
git pull origin cursor/cfb-matchup-response-sweep-1bf8
python3 scripts/cfb/sweep_matchup_response.py
```

That script:

1. Asserts production `MATCHUP_RESPONSE == 1.40`.
2. Loads the #543 v1 universe once (Layer A + lake_only closes + prior-year efficiency).
3. Sweeps 0.90 → 1.40 by 0.05, extends below 0.90 only if the curve is still falling, then refines ±0.04 by 0.02.
4. Scores Train-0 / Val-0 / Val-1 vs **actual** (MAE, RMSE, signed bias, MedAE) plus close/tail/ATS diagnostics.
5. Refuses to select a coefficient because it is closer to close.
6. Writes this file and `cfb-matchup-response-sweep-20260912.json`.
7. Emits exactly one of: `COEFFICIENT CANDIDATE EARNED` / `BROADER MODEL RECALIBRATION REQUIRED` / `INSUFFICIENT EVIDENCE`.

Unit tests in `tests/test_cfb_matchup_response_sweep.py` prove the overlay does not mutate 1.40 and that a Vegas-clone (better vs close, worse vs actual) is not selected.

## Sensitivity table

_Not scored. This cloud VM cannot see the legal lake. No fabricated rows._

## Comparison vs frozen 1.40 (Val-1)

Published #543 reference only (not re-measured here):

| Metric | frozen 1.40 (PR #543) |
| --- | ---: |
| n | 717 |
| MAE vs actual | 16.65 |
| bias vs actual | +10.10 |
| bias vs close | +11.34 |
| high-tail n (≥68) | 217 |
| high-tail bias vs close | +17.79 |
| mean model total | 63.84 |
| mean close total | 52.50 |
| mean actual total | 53.74 |

## Tail inflation

Unknown on any candidate other than frozen 1.40. The 1.40 tail pathology from #543 is unchanged because no overlay was scored.

## How to finish the fit

Relaunch **this same branch / same script** with `usePrivateWorker=true` on Ryan’s Mac (the #543 worker). Do not copy parquet. Do not spend Odds API credits. Do not open 2025 or 2026.

## GO / STOP

**INSUFFICIENT EVIDENCE**

STOP. Do not touch 2025, 2026, production CFB, PLAY labels, or Line Curve. Do not write a new production coefficient in this assignment.
