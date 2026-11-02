# CURSOR ADDENDUM t5155u — R5 Phase 1 FREEZE (DEV_R5_496)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5155u **659cd7d9** · Cos ORDER **3e14602b**
Worker A. Parallel Worker B owns N1 + market intersection + integration-owner combine.
Parent tip **f7ec09ee** (t5151u Package A stamp).
Implementation tip **661df712**.
**STOP — awaiting Alex preflight + Cos bind.** No target scoring loader. No EVAL.

Closed quality not reopened: #700 tip **12ccc482** / stamp **9d436eb1** ·
Alex **f4147e76** · Cos **4b23584a** = component ACCEPT only.
RETURN **7057e5a9** preserved.

## What this is

New **opt-in** `DEV_R5_496` record / directory / command. Phase 1 only.
Preserves all earlier runners, forecasts, and results. Not EVAL / production /
market-edge / GREEN. No ML / totals / joint from point margin.

Isolated path. Does not race-edit Worker B files
(`metric_cohorts.py` numerical strengthening, `eval_result_contract.py`,
`verify_integrate.py`, N1, market intersection).

## STEP 1 — FEATURE_RECON_REG496 identities frozen first

240 + 256 REG W2+ at #698 **c58ec422** / **bc1b62fc**. 2021 REG W18 kept (16).
Six 2020 Wild Cards refused. Membership = `season_type=REG` on
`schedule_results_2020_2023.csv` — **not** week≤18.

| Pin                         | sha256                                                             |
| --------------------------- | ------------------------------------------------------------------ |
| Feature JSON                | `282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c` |
| Feature matrix              | `a3b9d8ecb94902078ddcb89206a5a1ff16d5f1a3b4e8080186238d6578c52409` |
| FEATURE_RECON_REG496 ident. | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640` |
| DEV_IF437 ident.            | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| REG schedule                | `0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479` |

Schedule order first ID `2020_02_ATL_DAL`. Artifact order first ID
`2020_02_CIN_CLE`. Sets match; sources differ.

All **27/27** required inputs validated on the frozen matrix: DERIVED_PREGAME,
finite numerics, source sha + lineage, labels **RECONSTRUCTED** / **RETRO_FIT**.
`n_complete_27=496` · `n_partial=0`.

## Fixed arms

| Arm       | Pin                                                                                          |
| --------- | -------------------------------------------------------------------------------------------- |
| IF        | produce_μ @ `6ca03716` · sim `52d9e909` · fw `a0051cc4` · N=4000 · existing per-game seed     |
| Q2 coeffs | A=`2.5637441292077354` B=`1.660624056183471` ridge=20 prior_reg=0.5 · 2013–16 transfer · no refit/search |
| Candidate | `0.5*IF+0.5*Q2` exactly                                                                      |
| R3        | w=0.75 **STOP** `81b6c0fc` stands                                                            |

## R5 history rule (disclose ≠ old kickoff-only as-of)

Old as-of (`cf514078`) allowed same-week earlier kickoffs. R5 does **not**.

Q2 state = canonically identified REG score history from approved 2013–2021
sources only. For a target: earlier seasons + strictly earlier NFL weeks with
kickoff < KO−60. No same-week / own-target / later rows. No week≤18 REG proxy.

| Source                         | sha256 / status                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------- |
| games.csv kickoff              | `4fe1cdd7…` present · **no season_type**                                        |
| outcomes 50bda875              | `50bda875…` present · score-only · **no season_type**                           |
| schedule 2020–23               | `08533423…` · `season_type=REG` proves 2020 (256) and 2021 (272)                |
| 2013–2019 REG identity / prior | **UNPROVEN** — no approved season_type=REG extract; week≤18 proxy refused       |

**HOLD Q2** for all 496 with that missing proof. IF pipeline finished. No
invented history. Candidate withheld while Q2 is HOLD.

## Forecasts (Phase 1)

| Result              | Value        |
| ------------------- | ------------ |
| n_forecasts         | **496**      |
| n_if_finite         | **496**      |
| n_q2_hold           | **496**      |
| n_candidate_finite  | **0**        |
| target labels loaded| **0**        |

Seeds / IF tip / simulator / framework / source / history hashes / warnings
are in `FORECASTS_DEV_R5_496.json`. No home/away scores, no actual margin.

## Common 437 vs immutable old IF freeze

Old freeze `FORECAST_FREEZE_t5112u.json` sha `9e704b98…` (immutable).

| Check                                      | Result                          |
| ------------------------------------------ | ------------------------------- |
| 27-input last-played vs exact-week         | **437 / 437 identical**         |
| IF replay `1e-9*max(1,\|old\|)` same pin/seed | **437 / 437** · **0 BLOCKER** |
| Example `2020_02_CIN_CLE`                  | `m_if=0.07714026611934685` seed 672662 exact match |

No input discrepancy to explain on the 437. new59 = 30 (2020) + 29 (2021)
from frozen identities (not outcomes).

## Isolated package

`data/ops/nfl-t5155u-r5-496-freeze/`

| File                                         | sha256                                                             |
| -------------------------------------------- | ------------------------------------------------------------------ |
| `SPEC.json`                                  | `4cd87c0f8f898e63926903e8b3a6c9ab6e6c74edba21fb60a65272dc10b9f1e5` |
| `IDENTITY_MANIFEST.json`                     | `c94200d4f344207bf06a24185d7a424bb736229588dd53eb4ce7ee35ea466fd0` |
| `FEATURE_VALIDATION.json`                    | `3e0d40b936e5bc2dcdd08e4e1f28f07ffbd77f7d81d37a5023984937574b7690` |
| `Q2_HISTORY_FREEZE.json`                     | `5c34107e1ee7a15e2d910658b39e4224b305eebc9719416c4bb6ef061f916c9d` |
| `SPLIT_SCAFFOLDING.json`                     | `0b7a7d1ea26d6563a16cb79dd3417c57346164516b9816a7314a1b565f8cc20c` |
| `FORECASTS_DEV_R5_496.json`                  | `96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407` |
| `COMPARE_437.json`                           | `a0a54294eb7f05df3d3543b373394a99d438d7faa6b95ef945b59d66f2af5384` |
| `STOP_AWAITING_ALEX_PREFLIGHT_AND_COS_BIND.json` | `ebd995d55e32652901ea5687f7debdf8a48152a7323cc320ee8a358cb7c6da7b` |
| `PHASE2_POSITIVE_PATH.json`                  | `bca0143f9ae1270193bc5d2a66499f896743eac9e857f40448d21a42b73e0086` |
| `SCORING_REFUSE.json`                        | `83f1e775d34742eb36c969baeb4fe218908f526f992ae1037a7dcb37c07288ad` |
| `SOURCE_PINS.json`                           | `43a21807286da1b5594fe07d913459b3b30ba19eee08ec7fb2e4d1b71e85c144` |
| `FREEZE_MANIFEST.json`                       | `f19cb3c275553b3dda70b97c9d0a1a99802eea6081458b60210f7c95231b78b1` |

Code sha `r5_496_freeze.py` =
`24d118bb2453107002779937613de83ac27160ac4c9ca3d2cf7adb0298bf09ea`.

Command:

```
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_496_freeze_t5155u.py
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_496_freeze_t5155u.py --score
# → refused; outcome_loader_reads=0
```

## STOP hooks (zero target labels)

`check_cohort_before_target_outcome_loading` is wired on the Phase 1 command.
`--score` / `--eval` / `--load-targets` refuse with spy **reads=0**.
Hooks never invoke the loader. Phase 2 positive path is documented, not executed:

1. Alex source/numerical-identity PREFLIGHT GO
2. Cos bind / EXEC release
3. Hook ok on frozen FEATURE_RECON_REG496 IDs
4. Then load target scores for those IDs only
5. Score IF / Q2 / candidate home-margin. Still no market-edge / GREEN.

## Tests

```
cd services/model-service && PYTHONPATH=. python -m pytest \
  tests/test_nfl_t5155u_r5_496_freeze.py -q
```

13 passed: identity 496 + W18 + WC refuse; 27-input validate; Q2 HOLD + missing
2013–19 proof; week≤18 proxy refuse; history filter (same-week / own / later /
KO−60); candidate 0.5/0.5 and R3 0.75 STOP; IF replay tol + BLOCKER;
scoring spy zero reads; Phase 2 documented not executed; stubbed 496 IF +
Q2 HOLD; one real produce-μ; committed freeze hashes.

## Holds

Q2 leg HOLD — 2013–2019 REG identity/prior unproven.
R3 STOP 81b6c0fc. R2-C / Stage C unchanged. No 2022–23 regen/scoring.
No 2024–26. No Q2/2017 reopen. No merge / deploy / secrets / paid pulls /
new installs. No #700 re-review.

**STOP for Alex preflight + Cos bind before any target scoring loader.**

CERT=0.

## Pins

| Item               | Value                                                              |
| ------------------ | ------------------------------------------------------------------ |
| Implementation tip | `661df712a804bc1d9662f77008af28f8418cd0a1`                         |
| Parent tip         | `f7ec09ee2ffcce7b130c9b858304bbe8006a4428`                         |
| FEATURE_RECON_REG496 identity | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640` |
| Feature JSON       | `282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c` |
| Forecasts          | `96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407` |
| Freeze manifest    | `f19cb3c275553b3dda70b97c9d0a1a99802eea6081458b60210f7c95231b78b1` |
