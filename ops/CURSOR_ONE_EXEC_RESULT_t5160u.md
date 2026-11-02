# CURSOR ONE EXEC RESULT t5160u — CONSUMED (CERT=0)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: Cos ORDER t5160u ONE DEV **b319c428** · Alex APPEND GO **da9668eb**
· Cos ACCEPT **d0cc1ed6**. BIND md **3c78c645** / BIND json **537ce672**
not readable on this box — recreated from live pins. Cos claim token
**4fa6d856** (was UNSPENT / never machine-created; t5162u reconcile
**3c978ef9**). Supersedes premature ORDER **5d029306**.
Same authorized look. Not a second look. No auto-rerun.

Base tip **67e43c4c43a64f9d7e4e69dc98d15bac8ccffa71** · stamp/PR head
**d6088d21654ef5eb3f7481f4f0b507bbecd9c1e0**. Live runner hashes MATCH
Cos pins. PROTOCOL DEVIATION disclosed (255adf78 engineering-path
exposure). Bound EXEC used `schedule_outcome_loader` after verified
claimed hash-matching bind. `outcome_loader=None` — CLI only.

## Gate

| Check | Result |
| --- | --- |
| Implementation tip 67e43c4c | present; HEAD was stamp `d6088d216` (docs-only) |
| runner_code | `5fe3af1c…1d672d57` MATCH |
| runner_input | `69feb018…1ac8e0` MATCH |
| runner_spec | `9b32070e…a3e5c6` MATCH |
| forecast / IF | `96d3aa6f…5af407` MATCH |
| IDENTITY | `561ae3e1…ef8b3f` MATCH |
| Q2 | `eeb6fff7…06cc04` MATCH |
| CANDIDATE | `2f9a73e6…9a87c7` MATCH |
| market bytes / id | `072e99e0…` / `558fbfe5…` MATCH |
| REG496 cohort | `6429f859…9c640` MATCH |
| ONE_RUN before bind | MISSING |
| CLI | `--score --cos-bind` once · exit 0 · no caller loader |

## Status: CONSUMED

Machine `bind_id` `4eef5d1f843bb17327d0d81d3cdae3a8d7d91917d9763691b55808c365d0caa6`
(sha256 of live code/input/spec/forecast/cohort + alex_go_id `da9668eb`).
Cos claim token **4fa6d856** is the pre-machine name from BIND seals
that were not on this box.

| Timestamp | UTC |
| --- | --- |
| bound_at | 2026-11-02T04:45:42Z |
| claimed_at | 2026-11-02T04:45:46Z |
| consumed_at | 2026-11-02T04:45:51Z |

| Item | Value |
| --- | --- |
| labels READ | **1** (`schedule_outcome_loader` once) |
| metrics COMPUTED | **yes** — candidate+IF+market |
| result WRITTEN | **yes** |
| status | PHASE2_ONE_EXEC_BOUND_SCORED / STOP_BOUND_ONE_EXEC_NOT_EVAL |
| nfl_green / EVAL | false / null |
| reporting_class | DESCRIPTIVE_ONLY (market n=96 < 100) |

## Metrics (bound EXEC)

| Split | n | mae_if | mae_q2 | mae_candidate |
| --- | ---: | ---: | ---: | ---: |
| full496 | 496 | 11.191978 | 10.834458 | 10.852834 |
| old437 | 437 | 11.363783 | 11.029384 | 11.040111 |
| new59 | 59 | 9.919454 | 9.390686 | 9.465708 |

market∩96 n=96 · IF vs market mean signed Δ **1.150327** (game CI excludes 0) ·
candidate vs market **0.619575** (game CI INCONCLUSIVE). B=10000 seed 20261101.

## Artifacts

| Artifact | sha256 |
| --- | --- |
| ONE_RUN.json | `9a72c55be94e0fc04778da22748a70b2e159c4c95e4803c41449cbb8abfc13cc` |
| RECEIPT.json | `f8da3deab88858405fc55c0af829fde53ef4a689b697cd7a773442e564355869` |
| claim | `54ab3ab90ad079d15b183aeb6130a885a54501015d920ca89ea4c81c29720c11` |
| result json | `4b0ea24a2443964ad0a572577d5b71f52bf2c4bcec8f2cbb60b77763eeb8fb60` |
| PROTOCOL_DEVIATION.json | `58d26a4cab45293255a4cdb2a7946f244d6afa7fe65ca3a5e51cb1ca86662a42` |
| RECEIPT output_sha256 | `a5fddcfbd9060488a2a6f1886b4b8b641cb65f55174246f8b51782d49e8d2d96` |
| bind_id | `4eef5d1f843bb17327d0d81d3cdae3a8d7d91917d9763691b55808c365d0caa6` |
| Alex APPEND GO | `da9668eb` |

CERT=0 · DRAFT≠merge · no merge · failure≠second look.
