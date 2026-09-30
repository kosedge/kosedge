# NCAAM Fair Lab — Experiment Registry

## Active / frozen candidates

| Candidate ID | Method                                    | Role                       | Default?              | Status                                                                                                                       |
| ------------ | ----------------------------------------- | -------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `B2-C0-v1`   | `kenpom_adjem_plus_hca_v1`                | Incumbent B2               | **YES** (materialize) | Frozen historical                                                                                                            |
| `B2-PACE-v1` | `kenpom_adjem_pit_tempo_plus_game_hca_v1` | Unit-correction challenger | **NO**                | Frozen for Train-A diagnostics; Phase 2.7A immutable HCA/clips + non-finite fail-closed; awaiting pocket/holdout unseal auth |

Research alias `C3` refers to `B2-PACE-v1` in Phase 1B notes only.

## Window classifications

| Window                              | Role for H1/open-shrink                    | Role for B2-PACE-v1                                     |
| ----------------------------------- | ------------------------------------------ | ------------------------------------------------------- |
| Train-A (2022-11-07→2023-03-12)     | Fit / diagnose                             | Fit / diagnose / freeze evidence                        |
| **Test-A (2023-11-06→2024-01-28)**  | **Development-exposed**                    | **Development-exposed**                                 |
| pocket_2025 (2025-11-01→2025-12-31) | Sealed OOS (not for H1 confirm if exposed) | **Sealed confirmation** (requires explicit Ryan unseal) |

### Why Test-A is development-exposed for B2-PACE-v1

Test-A residual structure and large-disagreement failures against B1 contributed directly to the unit/possession-correction hypothesis. Therefore Test-A may be reported historically but **cannot** serve as untouched confirmation for `B2-PACE-v1`.

## Registered / research challengers (not promoted)

| Candidate ID         | Intent                                                      | Status                                                                                        |
| -------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `B2-PACE-NEUTRAL-v1` | Zero HCA when `venue_status=confirmed_neutral`; else 2.8696 | Frozen preregistration + research plumbing (2026-09-09). Train-A evidence only. Not promoted. |
| `B2-NEUTRAL-HCA-v1`  | historical alias only — do not implement under this ID      | superseded by `B2-PACE-NEUTRAL-v1`                                                            |

## Product exposure lock

No board, API, article, or UI path may consume `B2-PACE-v1` or `B2-PACE-NEUTRAL-v1` without a later explicit promotion decision. Materialize remains on incumbent only. Do not use KosEdge August 31 research ratings as published Week 2 KEI or production fair lines.
