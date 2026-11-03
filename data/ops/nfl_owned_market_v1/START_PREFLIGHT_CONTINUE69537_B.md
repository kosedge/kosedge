# START_PREFLIGHT_CONTINUE69537_B

CERT=0. OWNER CONTINUE 69537 t5320u under 86257 / 47318 / 58426.
Capacity gate BEFORE any restore or code. Cos-host PAUSED. No Cos staging.

| field | value |
|---|---|
| continue | 69537 |
| delta | 58426 |
| return | 47318 |
| ticket | t5320u |
| owner_clear | 86257 |
| worker | B |
| worker_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| filesystem | /dev/vdc on / (ext4) |
| workspace | /agent/repos/kosedge |
| branch | cursor/nfl-owned-market-v1-79df |
| start_tip | a8184e52cd14d2d4e1b394601ae7256b521da017 |
| written_utc | 2026-11-03T19:32:51Z |
| written_est | 2026-11-03T14:32:51-0500 |
| hard_end | 17:00 EST / 22:00 UTC |
| cos_host | PAUSED · no Cos-host work · no Cos staging |

## `df -h` (this Cursor worker host only)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

`findmnt -T /agent/repos/kosedge`: SOURCE `/dev/vdc` TARGET `/` FSTYPE ext4 SIZE 253.3G AVAIL 245.3G.

| path | free bytes | free GiB | threshold | result |
|---|---|---|---|---|
| /agent/repos/kosedge | 263415865344 | 245.325142 | 15 GiB | PASS |
| /tmp | 263415865344 | 245.325142 | 15 GiB | PASS |
| / | 263415865344 | 245.325142 | 15 GiB | PASS |

**GATE 0: PASS** (245.325142 GiB free on `/dev/vdc`). Ownership: this Cursor worker (`bc-02a716be`). Cos host not used.

## Preserve (DELTA 58426 / Cos 3b9549a5)

- 187 identities / 400 IDs · ADMISSIBLE@7834cbc7 · FREEZE 96/496
- synthetic risk1 · OWNED original locators
- remaining_blocker = freeze#limitations clock unverified
- owned_completion_claimed=false
