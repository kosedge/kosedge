# START_PREFLIGHT_CONTINUE69537_A

OWNER CONTINUE 69537 · DELTA 58426 · RETURN 47318 · CLEAR 86257 · t5320u · CERT=0
Worker A sole integration · Cursor host only · Cos-host PAUSED unused

## Host identity / ownership

- hostname: `cursor`
- uname: `Linux 6.12.94+ x86_64`
- workspace: `/agent/repos/kosedge`
- worker_id: `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8`
- branch: `cursor/r7-correctness-v1-abb8`
- base tip: `6d7330ff4c068257dde41632bfedfffa21f1db2f`
- Cos host: NOT USED (PAUSED)

## Disk (`df -h` on this worker)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

- workspace filesystem: `/dev/vdc` mounted at `/`
- free GiB: `245.32`
- required: `≥15 GiB`
- Cos `/dev/vdb`: PAUSED · not measured · not cleaned

## Verdict

**PASS** — 245.32 GiB free on `/dev/vdc` ≥ 15 GiB.

Written 2026-11-03T19:32:00Z before any CONTINUE 69537 code change.

## GATE0 recheck (this turn, 2026-11-03T19:35:42Z)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

- free: **246 GiB** on `/dev/vdc` mounted at `/`
- ownership: Cursor worker `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8` (Ryan Kos) · Cos-host unused
- verdict: **PASS** · Cos host not used
