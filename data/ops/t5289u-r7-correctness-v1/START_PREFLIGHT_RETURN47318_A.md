# START_PREFLIGHT_RETURN47318_A

OWNER RETURN 47318 · CLEAR 86257 · t5304u · CERT=0
Worker A sole integration · Cursor host only · Cos `/dev/vdb` HELD unused

## Host identity

- hostname: `cursor`
- uname: `Linux cursor 6.12.94+ #1 SMP PREEMPT_DYNAMIC Mon Nov  2 21:34:19 UTC 2026 x86_64`
- uid: `ubuntu` (1000)
- workspace: `/agent/repos/kosedge`
- worker_id: `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8`
- branch: `cursor/r7-correctness-v1-abb8`
- base tip: `2bdc58e8682935c567890236efa4da631a29d879`
- Cos host: NOT USED

## Disk (`df -h` on this worker)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

- workspace filesystem: `/dev/vdc` mounted at `/`
- free bytes: `263435907072` (shutil.disk_usage)
- free GiB: `245.32`
- required: `≥15 GiB`
- Cos `/dev/vdb` ~9.6 GiB: HELD · not measured · not cleaned

## Verdict

**PASS** — 245.32 GiB free on `/dev/vdc` ≥ 15 GiB.

Written 2026-11-03T16:32:00Z before any RETURN 47318 code change.
