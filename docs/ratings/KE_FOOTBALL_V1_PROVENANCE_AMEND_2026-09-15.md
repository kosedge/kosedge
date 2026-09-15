# KE Football v1 — provenance taxonomy amend

**Date:** 2026-09-15  
**Status:** `MEASUREMENT_PHASE1` · `production_promote=false`  
**Supersedes (taxonomy only):** `#569` three-layer table in [`KE_FOOTBALL_V1_SPEC.md`](./KE_FOOTBALL_V1_SPEC.md) §2 and the layer legend in [`KE_FOOTBALL_V1_METRIC_MATRIX.md`](./KE_FOOTBALL_V1_METRIC_MATRIX.md) / [`.json`](./KE_FOOTBALL_V1_METRIC_MATRIX.json).  
**Does not supersede:** metric definitions, hard stops, #562 REVISE, board dark, or the #560 fitted ridge as a live book.

Ryan reviewed #569 and authorized **Phase 1 measurement only**. This amend is the first code+docs change: the layer list is now four values.

---

## Canonical layers

```text
RAW → DERIVED → ADJUSTED → MODELED
```

| Layer        | Meaning                                                                 | Allowed in Phase 1                                                                                          | Forbidden                                                                                          |
| ------------ | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **RAW**      | Directly observed football events / statistics                          | Play flags, yards, EPA column as published by the owned PBP source, down, distance, score, clock, play type | A z-score, a 0–100, a ridge estimate, a 50                                                         |
| **DERIVED**  | Deterministic KE calculation from RAW                                   | Means, rates, plays/game, opportunity / PPO, seconds/play when clock is certified                           | Opponent effects of any kind; silent league-average substitution; SP+ z heuristics                 |
| **ADJUSTED** | Deterministic, point-in-time opponent adjustment of a DERIVED quantity  | Leave-one-game-out SOS using only `week < W` opponent DERIVED books                                         | Fitted `off_i`/`def_j`; ridge; decayed priors mixed into the number; `h × n_plays` as points       |
| **MODELED**  | Estimated / fitted outputs                                              | **Not implemented in Phase 1.** #560 joint-ridge remains a research MODELED candidate (`promote=false`)     | Relabeling ADJUSTED SOS as MODELED; inventing a new fit; using #562 to retune                      |

Rules unchanged except the new middle layer:

1. No synthetic proxy may be labeled as the real metric.
2. No 50-fill or identity constant may silently enter a KE rating.
3. Missing required information → `DATA_INSUFFICIENT` **or** an explicitly documented `PARTIAL`.
4. Native football units stay the identity of the number.
5. Do not optimize against ATS, closing lines, or betting ROI.
6. First validation = football / out-of-sample predictive validity.

---

## Why ADJUSTED exists

#569 put opponent-adjusted EPA in **MODELED** because the written SoT was a fitted two-way (`y = μ + h·home + off + def`). That is still correct **for a fitted estimator**.

Phase 1 measurement must expose an opponent-adjusted view that is **point-in-time safe** without fitting. That calculation is not a model:

```text
off_adj(team, W) = off_raw(team, week < W)
                 − (mean_j [def_raw(opp_j, week < W, exclude game g)] − league_def(week < W))
```

Same family on defense (offense-created by opponents). Week `W` consumes only information through `W−1`. Same-game opponent observations are excluded (leave-one-out). No λ, no n0, no prior blend, no HFA term.

- If the opponent has **no other** eligible games in the window → that matchup is `DATA_INSUFFICIENT` for ADJUSTED (not a 0, not league fill).
- Week-1-only windows therefore have **no** ADJUSTED EPA. That is correct.
- #560 ridge stays **MODELED**, research-only, not re-fit here, not promoted, not used as a coefficient source.

`ke.opp_adj_epa` in Phase 1 **is this ADJUSTED quantity**. The #560 object keeps its own research ID (`fit_joint_v2_joint_mu_hfa_n0_ridge`) and must not be emitted under the Phase 1 ID.

---

## Companion updates

| File | Change |
| ---- | ------ |
| This document | Authority for the four-layer list |
| `KE_FOOTBALL_V1_SPEC.md` §2 | Four layers; `ke.opp_adj_epa` Phase 1 = ADJUSTED; #560 = MODELED candidate |
| `KE_FOOTBALL_V1_METRIC_MATRIX.md` / `.json` | `layers` includes ADJUSTED; opp-adj row split |
| `README.md` | Measurement Phase 1 is authorized; Team Strength is not |

---

## Still forbidden (unchanged)

Team Strength / KE Overall weighting · scoring-model integration · matchup interaction · market integration · production promotion · UI / public ratings · board reopen · PFF / new vendors · #562 coefficient tuning · silent fills.
