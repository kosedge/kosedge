# START_PREFLIGHT_DELTA58426_A

OWNER DELTA 58426 · RETURN 47318 · CLEAR 86257 · t5312u · CERT=0
Worker A sole integration · Cursor host only · Cos `/dev/vdb` HELD unused

## Host identity

- hostname: `cursor`
- uname: `Linux 6.12.94+ x86_64`
- workspace: `/agent/repos/kosedge`
- worker_id: `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8`
- branch: `cursor/r7-correctness-v1-abb8`
- base tip: `b956e6ca84d474a7a7c9fcfed78d7d54c828feca`
- Cos host: NOT USED

## Disk (`df -h` on this worker)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

- workspace filesystem: `/dev/vdc` mounted at `/`
- free GiB: `245.32` (246G avail from `df -h`)
- required: `≥15 GiB`
- Cos `/dev/vdb` ~9.6 GiB: HELD · not measured · not cleaned

## Verdict

**PASS** — 245.32 GiB free on `/dev/vdc` ≥ 15 GiB.

Written 2026-11-03T17:04:00Z before any DELTA 58426 code change.
