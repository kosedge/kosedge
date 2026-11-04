# START_PREFLIGHT_METADATA14083_A

OWNER CLEAR 92861 · METADATA 14083 · t5344u · CERT=0
Worker A sole integration · Cursor host only · Cos-host unused / quarantined

Written 2026-11-03T23:58:00Z **before METADATA 14083 package work**. ACK≠START.

Parent package: t5335u R7 followthrough preflight (`df041d6f` packaging / `2a2c91c9` executed CANDIDATE NOT_READY missing_n=5).
Staged evidence tip: `e290ff3b306d7c6c47b2d11a183c520992b90f59`.
Do **not** redo accepted math tests. SciPy ABSENT — no install. Science EXEC HOLD.

## 1. Disk (this worker)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

`df -B1 /dev/vdc`: Available `263409508352` bytes = **245.32 GiB**.

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

After prior FF onto staged evidence (this worker already at tip; no extra fetch this GATE0):

- `git rev-parse HEAD` = `e290ff3b306d7c6c47b2d11a183c520992b90f59`
- HEAD **equals** staged metadata-projection commit `e290ff3b`
- ancestors present: `df041d6f` (prior packaging) · `2a2c91c9` (spec / executed NOT_READY) · `d3f2c56a` (CONTINUE 69537)
- subject: `evidence: stage R7 metadata identities and recorded schedule; preserve unknown actual clocks`

**PASS**

## 4. Path-read + SHA256

Projection path: `research/nfl_followthrough_20261103/R7_METADATA_PROJECTION.json`

```
9306a1b5ea74e71de652e4e27761f5814c349ecd1415a3507336d31f8703bbc9  research/nfl_followthrough_20261103/R7_METADATA_PROJECTION.json
```

Order required: `9306a1b5ea74e71de652e4e27761f5814c349ecd1415a3507336d31f8703bbc9`

Spec path still present:

```
2f3c215d7680dd5aa33a0a77690ece4ef70a0a8dbbebaac880750dd776ec66d7  research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md
```

**PASS** — projection SHA256 MATCH · spec SHA256 MATCH

## 5. Temp-write (create + delete)

Allowed ops path on this host:

- created: `data/ops/t5335u-r7-followthrough/.gate0_meta14083_11983.tmp`
- sha256: `43819670022082ed49b107e21dad0f3414f733ee2144b0992847176b5ed27440`
- deleted: yes (`test ! -e` after `rm`)

**PASS**

## Verdict

**GATE0 PASS** — disk 245.32 GiB · ownership A/#716 · HEAD=e290ff3b · projection SHA256 MATCH · spec SHA256 MATCH · temp-write OK.

METADATA 14083 may start. Cos-host unused. CERT=0. No NTBB-K kernel. No fictional R7 re-exec. No score/forecast reconstruction.
