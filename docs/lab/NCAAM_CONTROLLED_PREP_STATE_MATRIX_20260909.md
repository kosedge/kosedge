# NCAAM controlled preparation — authoritative state reconciliation

**Base:** `origin/deploy-vercel` @ `4bd0f87de71d23cca8d61c980530a0902b3e8b36`  
**As of:** 2026-09-09  
**Lane:** A (research / reversible only)  
**Builder findings are not independent approval.**

## Observed facts (repo + GitHub)

| Item                                  | Observed state                                                                                                                      | Evidence                                                                                      |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Phase 2.6F foundation (PR A #500)     | **MERGED** 2026-09-07                                                                                                               | merge `729c07ce…` is ancestor of tip                                                          |
| Phase 2.6F governance (PR B #501)     | **MERGED** 2026-09-07                                                                                                               | merge `beae0013…` is ancestor of tip                                                          |
| B2-PACE-v1 challenger (PR #490)       | **MERGED** 2026-09-05                                                                                                               | merge `9e755056…`; materialize remains incumbent-only                                         |
| Later production after #504           | camp desk #509, NFL customer-truth #508, odds budget #505–#507                                                                      | no NCAAM challenger / holdout mutation                                                        |
| Sealed holdout package                | `ncaam_holdout_2024_25_v1_1` sealed; `features_labels_joined_for_evaluation=false`; `performance_metrics_calculated` absent / false | `data/ops/lab/ncaam/holdout_2024_25/seal/seal_receipt.json` (`seal_payload_sha256=af4fd451…`) |
| B1 incumbent                          | Close-consensus baseline for Lab scorecards; not a fair-engine candidate                                                            | Protocol / scorecard docs                                                                     |
| B2-C0-v1 incumbent fair               | **YES** materialize default                                                                                                         | `fair_b2.py` + experiment registry                                                            |
| B2-PACE-v1                            | Frozen unit-correction challenger; Train-A diagnostics + Phase 2.7A immutable HCA; **not** production default                       | `fair_b2_pace_v1.py` sha256 `4a305870…`                                                       |
| Neutral-site handling (pre this prep) | SoT packs carry `neutral_site`; Lab fair engines ignore it; venue contract exists for holdout foundation only                       | Phase 2.5 hardening + `venue_contract.py` sha256 `9f48eb26…`                                  |
| Train-A                               | 2022-11-07→2023-03-12 development window; parquet present locally                                                                   | protocol + `ncaam-fair-lab-train_a-latest.parquet`                                            |
| Test-A                                | **Development-exposed** for B2-PACE family; not untouched confirmation                                                              | experiment registry                                                                           |
| Sealed 2024–25 holdout                | Sealed; **must not** unseal / score in this lane                                                                                    | seal receipt + Phase 2.5/2.6F governance                                                      |
| Prior draft PR #510                   | Same-day 973f prep (DO NOT MERGE)                                                                                                   | exists; this `-ae7a` lane is the isolated continuation                                        |

## Current-state matrix

| Topic                                                         | Status bucket                                                                                 |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Phase 2.6F foundation + CR8 fail-closed schedule              | **completed** (merged)                                                                        |
| B2-PACE-v1 freeze + Phase 2.7A immutable HCA                  | **completed** (merged; research challenger)                                                   |
| B1 close-consensus baseline wiring                            | **completed**                                                                                 |
| Train-A / Test-A cut windows documented                       | **completed**                                                                                 |
| Sealed holdout package + R2 refs                              | **completed** (sealed; not evaluated)                                                         |
| Neutral-site descriptive Train-A split (Phase 2.5)            | **implemented but unverified** as independent confirmation (builder counterfactual only)      |
| `venue_contract.normalize_venue_status`                       | **completed** for holdout foundation; **authorized preparation** to reuse for Lab fair inputs |
| B2-PACE-NEUTRAL-v1 preregistration + research plumbing        | **authorized preparation** (this lane)                                                        |
| Train-A NEUTRAL diagnostics (single run)                      | **authorized preparation** → research evidence only after run                                 |
| Pocket 2025 / holdout scoring of PACE or NEUTRAL              | **blocked pending independent validation** + Ryan unseal                                      |
| Promotion / materialize switch / board consumption            | **Ryan-only decision**                                                                        |
| Using Aug 31 research ratings as Week 2 KEI / production fair | **blocked** (explicit hard stop)                                                              |

## Inferences (not facts)

1. Merging PR #490 shipped the **research challenger code** without changing the materialize default; product boards should still read incumbent B2-C0.
2. Neutral HCA gating is the next atomic challenger after unit correction; Phase 2.5 already recorded a research counterfactual, not an implemented candidate.
3. Schedule SoT `neutral_site` is usable for Train-A joins but inherits ESPN labeling risk (semi-home tournaments).

## Recommendations (not approvals)

1. Freeze NEUTRAL preregistration before any comparative Train-A metrics (done in this lane).
2. Keep holdout sealed until Grok-reset independent validation of identity + PIT + gates.
3. Do not retune after seeing Train-A NEUTRAL numbers.
