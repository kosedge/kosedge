# START_PREFLIGHT_B

CERT=0. Worker B only. Isolated `nfl_owned_market_v1`. No commit claimed
before this receipt. Not a pass. Not certification. Not a shared-gate
registration.

| field | value |
|---|---|
| ticket | t5289u |
| owner_clear | 86257 |
| scope | chief-nflgreen-model-day-20261103-1700 |
| plan_fingerprint | b15d6cec143212067b896057a048cd51071981d6ea1b3561c08db89cb6355358 |
| worker | B |
| profiles | OWNED_MARKET_TRACE_V1 · SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 |
| window | 2026-11-03 09:00–17:00 EST / 14:00–22:00 UTC |
| hard_stop | 17:00 EST / 22:00 UTC |
| written_utc | 2026-11-03T14:05:00Z |
| written_est | 2026-11-03T09:05:00-0500 |
| status | PREFLIGHT_PASS |

## (1) Worker / agent id and hostname

| field | value |
|---|---|
| worker_label | Worker B |
| ticket | t5289u |
| cursor_conversation_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| cloud_agent_bcid | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| cloud_agent_url | https://cursor.com/agents/bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| hostname_f | cursor |
| uname | Linux cursor 6.12.94+ #1 SMP PREEMPT_DYNAMIC Mon Nov 2 21:34:19 UTC 2026 x86_64 |
| uid | ubuntu (1000) |
| whoami | ubuntu |
| sibling_A | bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8 (R7_CORRECTNESS_V1 sole integration; B does not write shared files) |

## (2) Isolated branch / workspace

| field | value |
|---|---|
| workspace | /agent/repos/kosedge |
| isolated_branch | cursor/nfl-owned-market-v1-79df |
| starting_HEAD | f5e3bb58ccbe5a8892fed2a01f347c2308394a2f |
| starting_HEAD_branch | origin/deploy-vercel (fetched; local matched remote) |
| isolation | own branch; B writes only nfl_owned_market_v1 paths |

## (3) Source pins resolve (full shas)

| pin | requested | full sha | note |
|---|---|---|---|
| R6 A | 54b08a301cf824c79ee3203180a51e2d832bb6f9 | 54b08a301cf824c79ee3203180a51e2d832bb6f9 | `t5218u R6 TIMING DELTA: seal=cutoff=KO-60, strictly precede (CERT=0)` |
| R6 B | afb13301b5c7e3b8780a8dd1f85145e91bebef55 | afb13301b5c7e3b8780a8dd1f85145e91bebef55 | `draft(nfl): t5218u R6 TIMING DELTA seal=cutoff=KO-60 (CERT=0)` |
| #713 gate tip | 679dbdaf | 679dbdaf8c9044edffb34ffca1543c33eea77db7 | PR https://github.com/kosedge/kosedge/pull/713 · DRAFT · `cursor/nfl-ops-v1-evidence-manifest-gate-13a1` |
| #714 | (not a base) | 5558890b5f8a66c16c658fce2971f0a7e2f2c7de | PARTIAL · not a base · PR https://github.com/kosedge/kosedge/pull/714 |

Fetch notes: `git fetch origin <full-sha>` succeeded for R6 A and R6 B.
`git fetch origin 679dbdaf` could not resolve a remote ref by short sha;
`git fetch origin pull/713/head` resolved the full tip
`679dbdaf8c9044edffb34ffca1543c33eea77db7`. #714 fetched as
`5558890b5f8a66c16c658fce2971f0a7e2f2c7de` and stays PARTIAL / not a base.

## (4) Allowed-path read works

| check | result |
|---|---|
| `services/model-service/src/services/` | readable (parent of isolated package) |
| `data/ops/` | readable (parent of isolated ops) |
| `services/model-service/tests/` | readable (parent of isolated test file) |
| `services/model-service/src/services/__init__.py` | readable · 0 bytes · `/agent/repos/kosedge/services/model-service/src/services/__init__.py` |
| `nfl_owned_market_v1` package / ops at start | absent (expected; isolated area not yet built) |
| pin objects via `git cat-file -t` | all three pins are `commit` |

## (5) Isolated temp write works

| field | value |
|---|---|
| mktemp dir | `/tmp/start_preflight_b.RnJZlo` |
| write | `preflight-b-ok\n` → `probe.txt` |
| read | `preflight-b-ok` |
| probe sha256 | `5eb75e2578d388a6b40e50fe79a9ab0e237a4c6c995aca12db67d9e759b8ff31` |
| delete | file removed; directory removed; `temp_deleted=1` |

## (6) No conflicting writer on B paths

| check | result |
|---|---|
| `git log --all -- '*nfl_owned_market_v1*'` | empty |
| remote path count on deploy-vercel / #713 / #714 / R6 A / R6 B / chief-nflgreen plan A+B | 0 |
| open PRs titled/searching `nfl_owned_market_v1` / `OWNED_MARKET_TRACE` / `t5289u` | none |
| cloud agents on these two profiles | this run only (`bc-02a716be…`); Worker A is R7 integration and has no branch yet |
| B will not edit | `nfl_ops_v1_evidence/*`, shared evidence gate, Worker A files |

## (7) Disk free on THIS host

`df -B1` — workspace and `/tmp` are the same volume `/dev/vdc`.

| path | 1B-blocks | used | available | threshold | pass |
|---|---|---|---|---|---|
| `/agent/repos/kosedge` | 271966244864 | 8514613248 | **263434854400** | 16106127360 (15 GiB) | yes |
| `/tmp` | 271966244864 | 8514613248 | **263434854400** | 16106127360 (15 GiB) | yes |

`BLOCKED_LEG=B_DISK` is **not** raised. No other host used or proxied.

## Milestone ETAs (EST)

| milestone | ETA | note |
|---|---|---|
| 09:30 EST preflight / interface checkpoint | 2026-11-03 09:30 EST | this receipt + profile names/schemas |
| 11:30 EST first executable artifact | 2026-11-03 11:30 EST | isolated produce/validate + fixtures |
| 14:00 EST hand-off to A | 2026-11-03 14:00 EST | HANDOFF_INTERFACE (names, schemas, fixture hashes) |
| 14:00–16:00 EST review fixes | 2026-11-03 16:00 EST | B-only isolated fixes if A flags interface |
| 16:00–17:00 EST evidence buffer | 2026-11-03 17:00 EST | no gate registration by B |
| HARD STOP | 2026-11-03 17:00 EST / 22:00 UTC | stop |

## Constraints restated

CERT=0. Synthetic fictional typed inputs only. No paid APIs / spend / new
sources / security / credential changes. No prod push / merge / deploy.
DRAFT PR only. No certification, public, or betting output. No protected
2024–26 / EVAL / Q2-2017 reopen. No R5 rerun-reset. No StageC-E1. No
R2HOLD/R3STOP lift. A alone registers the two profiles on R7_CORRECTNESS_V1.
