# START_PREFLIGHT_CLEAR92861_A

OWNER CLEAR 92861 · t5335u · chief-nflgreen-followthrough-20261103 · CERT=0
Worker A sole integration · Cursor host only · Cos-host unused / quarantined

Written 2026-11-03T23:25:52Z **before Phase 1 package work**.

## 1. Disk (this worker)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

`df -B1 /dev/vdc`: Available `263412932608` bytes = **245.32 GiB**.

- device: `/dev/vdc`
- mount: `/`
- required: ≥15 GiB
- Cos `/dev/vdb`: unused · not measured · not cleaned

**PASS**

## 2. Ownership

- hostname: `cursor`
- uname: `Linux 6.12.94+ x86_64`
- workspace: `/agent/repos/kosedge`
- worker_id: `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8`
- owning user: Ryan Kos (`kosryan11@gmail.com`)
- branch: `cursor/r7-correctness-v1-abb8`
- PR: https://github.com/kosedge/kosedge/pull/716 DRAFT
- Cos host: NOT USED

**PASS**

## 3. Head SHA / ancestry

After `git fetch origin cursor/r7-correctness-v1-abb8` and `git merge --ff-only`:

- `git rev-parse HEAD` = `2a2c91c9b839da2246a01596b203318295581914`
- HEAD **equals** staged NTBB-K spec commit `2a2c91c9`
- parent = `d3f2c56adcbb684db20af9c29a55e656371e605e` (preserved CONTINUE 69537 tip)
- `d3f2c56a` is ancestor of HEAD
- subject: `docs: freeze NTBB-K research family for synthetic-only follow-through`

**PASS**

## 4. Path-read + SHA256

R7 tree present:

```
services/model-service/src/services/nfl_r7_correctness_v1/calendar.py
services/model-service/src/services/nfl_r7_correctness_v1/config_adapter.py
services/model-service/src/services/nfl_r7_correctness_v1/consume_b.py
services/model-service/src/services/nfl_r7_correctness_v1/franchise.py
services/model-service/src/services/nfl_r7_correctness_v1/__init__.py
services/model-service/src/services/nfl_r7_correctness_v1/packets.py
services/model-service/src/services/nfl_r7_correctness_v1/pins.py
services/model-service/src/services/nfl_r7_correctness_v1/produce.py
services/model-service/src/services/nfl_r7_correctness_v1/q2_canonical.py
services/model-service/src/services/nfl_r7_correctness_v1/recorder.py
services/model-service/src/services/nfl_r7_correctness_v1/run.py
```

Spec path: `research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md`

```
2f3c215d7680dd5aa33a0a77690ece4ef70a0a8dbbebaac880750dd776ec66d7  research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md
```

Cos connector expected: `2f3c215d7680dd5aa33a0a77690ece4ef70a0a8dbbebaac880750dd776ec66d7`

**PASS** — MATCH

## 5. Temp-write (create + delete)

Allowed ops path on this host:

- created: `data/ops/t5289u-r7-correctness-v1/.gate0_clear92861_10618.tmp`
- sha256: `f213d58d186f5e7aa615cecc44bb5f47cc83621ae86bb7a3d2182af321639cdd`
- deleted: yes (`test ! -e` after `rm`)

**PASS**

## Verdict

**GATE0 PASS** — disk 245.32 GiB · ownership A/#716 · HEAD=2a2c91c9 (parent d3f2c56a) · spec SHA256 MATCH · temp-write OK.

Phase 1 may start. Cos-host unused. CERT=0. No NTBB-K kernel this turn.
