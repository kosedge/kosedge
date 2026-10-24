# Ryan CLEAR + IMV cites (opening-runner v5)

| sha8 | original path | sha256 | package copy |
|---|---|---|---|
| `0505e492` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v4.txt` | `0505e49295df6c0d3b3ddd2256607325da67baf561cc5d3b8a5a477fb669d508` | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v4.txt` |
| `4fd6cfbe` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v3.txt` | `4fd6cfbe0adeaa7ff0152d8833e15d6b4e49a64cf47350fe595f3d35acef2867` | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v3.txt` |
| `b746e5eb` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v3_ERRATUM_v1.txt` | `b746e5eba9c781f5f0586161b42d942a546b94224c24be8253f9cdd6a6d9ccf0` | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v3_ERRATUM_v1.txt` |
| `77d9c00a` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v2.txt` | `77d9c00a306d1399aeeab6558a522182aa52d63c42c0b1f8cc4d350c1b0c3d0d` | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v2.txt` |
| `a8958e85` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v1.txt` | `a8958e850cd75cce5a24feda95a865e86ca39a2afaff5144748f70cfe4dcbeaa` | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v1.txt` |
| `b7364186` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt` | `b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8` | `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_RUNNER_D2_v1.txt` |
| `fabf8732` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt` | `fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0` | `seeded/DECISION_RYAN_t4335s14919_HOLDOUT_CLEAR_v3_1_v1.txt` |
| `592e0bb9` | `/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt` | `592e0bb9e57ef4c7d997d48b336cb37594f7353a891b8ab56d6a70b55492e021` | `seeded/DECISION_RYAN_SCORER_V6_2.txt` |
| `8ca00bc4` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6.txt` | `8ca00bc49b412c1524b4a0d5a1ebacdd7bc4fe26f3e6354d52cb549812dbb012` | `seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6.txt` |
| `14ac1819` | `/workspace/fg-repair/imv-gate1-review-2026-10-02/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6_ERRATUM_v1.txt` | `14ac18190c89d3620a6f27d0a0be64fc8147c321063ca4aeaa459faa31fcde41` | `seeded/IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v6_ERRATUM_v1.txt` |
| `35cbb56e` | request v3.1 | `35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b` | `seeded/nfl-injury-holdout-request-2024-2025-v3.1.md` |
| `755d30a8` | scorer v6.2 + S-2 (AUTHORIZED; IMV diff re-check) | `755d30a8ce0dde7cd31b2e5ded9d4e06240e73f963b68a6ae4bd9af30d90ea5f` | `seeded/v6.2-draft/run_injury_residual_evaluator.py` |
| `ca98ae0e` | scorer v6.1 (diff baseline only) | `ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6` | `seeded/ca98ae0e/run_injury_residual_evaluator.py` |
| `ebd3dac0` | HEAD 8e2a15ac injury_paths QB1_INDEX_UNITS = 0.12 | `ebd3dac083562afb4928e2ed756f617248894e636356f7426f0bc6ae58344e8b` | `seeded/injury_paths_8e2a15ac.py` |
| `aa9d512b` | frozen row builder | `aa9d512bd061266e49cc7ec7eb5661da31427ae555c1636f09fd8c9c5353e741` | `holdout_frozen_row_builder.py` |
| `6409dcb8` | delta producer | `6409dcb8948a5b5ee8ca481ce28be77adf44d3335932ff18cb9e0392b0d3f5b1` | `holdout_delta_producer.py` |
| `5521961d` | expected answers v5 | `5521961d7adb75fdb4883182c615645bd95e070d539279903658f9bb4660ac6e` | `t_expected/HOLDOUT_EXPECTED.json` |

Store copies: `/cursor/stores/self/imv-inputs/<name>`.

Ryan `t4335s14919`: `CLEAR: build the runner, IMV reviews, then open once`.
Ryan `t4340s14953`: `Yes: allow scorer v6.2 for the opening, only if IMV passes the diff as holdout-allowance-only with no metric change`.
`0505e492`: opening runner v4 RETURNED. **Lock and opening are not allowed.**
This package is the v5 opening runner for IMV changes-only review. No real lock. No 2024/25 read.
Single scorer pin is `755d30a8`. IMV must re-check that sha versus `ca98ae0e`.
