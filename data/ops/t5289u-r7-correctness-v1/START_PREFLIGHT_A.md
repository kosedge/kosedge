# START_PREFLIGHT_A — t5289u CLEAR 86257 Worker A

**Verdict: PASS.** CERT=0. No commit preceded this receipt. No build work before PASS.

| Field | Value |
|---|---|
| ticket | t5289u |
| owner_clear | 86257 |
| thread | t5289u |
| scope | `chief-nflgreen-model-day-20261103-1700` |
| plan_fingerprint | `b15d6cec143212067b896057a048cd51071981d6ea1b3561c08db89cb6355358` |
| role | Worker A · SOLE integration / shared-file writer · `R7_CORRECTNESS_V1` |
| window | 2026-11-03 09:00–17:00 EST / 14:00–22:00 UTC |
| hard_stop | 17:00 EST / 22:00 UTC |
| receipt_utc | 2026-11-03T14:05:43Z |
| cert | 0 |

## (1) Worker / agent identity and hostname

| Field | Value |
|---|---|
| bc_id | `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8` |
| agent_name | t5289u CLEAR 86257 A R7_CORRECTNESS_V1 (sole integration) |
| url | https://cursor.com/agents/bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8 |
| hostname | `cursor` |
| kernel_hostname | `cursor` |
| uname | Linux cursor 6.12.94+ x86_64 |
| user | `ubuntu` |
| cwd | `/agent/repos/kosedge` |
| pod_cgroup | `pod-clzz6jywq5ci5gvh7ngbwr6fnq-02529fec` |
| CURSOR_CONVERSATION_ID | `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8` |
| CURSOR_AGENT | `1` |
| private_worker | false (this host only; no proxy) |
| owning_user | Ryan Kos `<kosryan11@gmail.com>` |

This host only. No other host used or proxied.

## (2) Isolated branch / workspace

| Field | Value |
|---|---|
| branch | `cursor/r7-correctness-v1-abb8` |
| starting_HEAD | `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f` |
| starting_ref | `origin/deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f` |
| workspace | `/agent/repos/kosedge` |
| created_from | local `deploy-vercel` matching `origin/deploy-vercel` |

No prior commits on this branch at receipt time.

## (3) Source pins resolve (git fetch + full SHA)

Fetched on this host. `#714` stays PARTIAL and is **not** a wholesale base.

| Pin | Requested | Full SHA | Subject | When |
|---|---|---|---|---|
| R6 A | `54b08a301cf824c79ee3203180a51e2d832bb6f9` | `54b08a301cf824c79ee3203180a51e2d832bb6f9` | t5218u R6 TIMING DELTA: seal=cutoff=KO-60, strictly precede (CERT=0) | 2026-11-02 15:56:06 +0000 |
| R6 B | `afb13301b5c7e3b8780a8dd1f85145e91bebef55` | `afb13301b5c7e3b8780a8dd1f85145e91bebef55` | draft(nfl): t5218u R6 TIMING DELTA seal=cutoff=KO-60 (CERT=0) | 2026-11-02 15:57:35 +0000 |
| #713 gate tip | `679dbdaf` | `679dbdaf8c9044edffb34ffca1543c33eea77db7` | draft(nfl): bind evidence-manifest DIRECT gates to runtime context (CERT=0) | 2026-11-03 04:16:56 +0000 |
| #714 (PARTIAL, not base) | n/a | `5558890b5f8a66c16c658fce2971f0a7e2f2c7de` | draft(nfl): t5279u tip-runtime evidence pack at 6c546d92 (CERT=0) | 2026-11-03 05:39:04 +0000 |

#713 fetched via `origin/pull/713/head`. PR: https://github.com/kosedge/kosedge/pull/713

Frozen IF/sim/framework pins (in-repo, this host):

| Pin | Expected | Observed on this checkout |
|---|---|---|
| `nfl_simulator.py` | `52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385` | MATCH |
| `nfl_handicapping_framework.py` | `a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3` | MATCH |
| IF tip | `6ca03716fe52930332d5ffba302c312a651980cc` | pin reused; tree not remounted |

## (4) Allowed-path read

| Path | Result | Bytes |
|---|---|---|
| `AGENTS.md` | READ_OK | 3643 |
| `NFL_SPREAD_PLAY_LOCKED.md` | READ_OK | 1949 |
| `services/model-service/src/services/nfl_simulator.py` | READ_OK | 41265 |
| `services/model-service/src/services/nfl_handicapping_framework.py` | READ_OK | 50756 |
| `services/model-service/src/services/nfl_canonical_teams.py` | READ_OK | 2952 |
| R6 A `nfl_t5208u/produce.py` via `git show 54b08a30:…` | READ_OK | (pinned tip) |
| #713 `nfl_ops_v1_evidence/gate.py` via `git show 679dbdaf:…` | READ_OK | (pinned tip) |

`AGENTS.md` sha256 `d3a28cd8cc5037ecc21c32522b4093214ec293622835514c6f8138d1e9debefe`.

## (5) Isolated temp write

```
tmp=/tmp/r7-correctness-preflight-A.RZy2xg
write: preflight-write-ok
sha256: f84bea44154f6c69d23205e0e5cbbd903a0b25f9e9f84fd422b46b98b74d4fd2
delete: tmp_deleted_ok
```

mktemp dir created, probe written, read back, file + dir removed on this host.

## (6) No conflicting writer on this branch or shared gate files

| Check | Result |
|---|---|
| This branch exists elsewhere? | NO. Created here. `git ls-remote` had no `cursor/*r7*correctness*` / `cursor/*t5289*` head. |
| Open PR for `R7_CORRECTNESS_V1`? | NONE |
| Shared gate files on `deploy-vercel`? | ABSENT (gate lives only on prior DRAFT #713 / #714) |
| Concurrent shared-gate writer today? | NONE on this branch |
| Worker B | `bc-02a716be-429a-56c8-ab0f-5f262aa479df` RUNNING · isolated `nfl_owned_market_v1` · does **not** touch shared files · does **not** register in the shared gate |
| Prior DRAFT #713 | `cursor/nfl-ops-v1-evidence-manifest-gate-13a1` · reused **narrowly** as gate tip `679dbdaf` · not a concurrent writer on this branch |
| Prior DRAFT #714 | PARTIAL · **not** a wholesale base · not checked out wholesale |
| Prior DRAFT #712 | worker-release handoff lineage only · not this day's Worker B |

Worker A is the sole shared-file writer for this window.

## (7) Disk free on THIS host (`df -B1`)

Threshold: 15 GiB = 16106127360 bytes.

```
Filesystem        1B-blocks       Used    Available Use% Mounted on
/dev/vdc       271966244864 8513560576 263435907072   4% /   # workspace
/dev/vdc       271966244864 8513560576 263435907072   4% /   # /tmp same volume
```

| Volume | path | available_bytes | ge_15GiB |
|---|---|---|---|
| `/dev/vdc` | `/agent/repos/kosedge` | `263435907072` | YES |
| `/dev/vdc` | `/tmp` | `263435907072` | YES |

`BLOCKED_LEG=A_DISK` does **not** apply.

## Milestone ETA (EST / UTC)

| Milestone | EST | UTC | Status at receipt |
|---|---|---|---|
| Preflight / interface checkpoint | 09:30 | 14:30 | this receipt + interface stub |
| First executable artifact | 11:30 | 16:30 | opt-in synthetic IF/Q2 producer |
| Integration | 14:00 | 19:00 | shared gate + paired recorder |
| Review fixes | 14:00–16:00 | 19:00–21:00 | |
| Evidence / report buffer | 16:00–17:00 | 21:00–22:00 | DRAFT PR only |
| HARD STOP | 17:00 | 22:00 | stop all work |

## Constraints restated (not lifted)

CERT=0 · targets 0/8 preserved · synthetic fictional typed inputs only · no paid APIs / spend / new sources / security / credential changes · no prod push / merge / deploy · DRAFT PR only · no certification / public / betting output · do not reopen protected 2024–26 / EVAL / Q2-2017 · no R5 rerun-reset · no StageC-E1 · no R2HOLD/R3STOP lift.

## Next (only after PASS)

1. Interface stub: Worker A registers `R7_CORRECTNESS_V1`; B profiles `OWNED_MARKET_TRACE_V1` + `SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1` stay `PENDING_HANDOFF`.
2. Narrow reuse of R6 A/B + #713 gate. `#714` remains PARTIAL / not base.
3. New opt-in synthetic IF/Q2 producer → shared evidence gate → paired recorder.
4. `REST_ACTUAL_ET_CALENDAR_V1` · franchise key · config bind · frozen IF/sim/framework pins.
