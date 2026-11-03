# START_PREFLIGHT_DELTA58426_B

CERT=0. OWNER DELTA 58426 t5312u under RETURN 47318 / CLEAR 86257.
Capacity gate BEFORE any restore or code. Cos DISK-1 HELD. No Cos staging.

| field | value |
|---|---|
| delta | 58426 |
| return | 47318 |
| ticket | t5312u |
| owner_clear | 86257 |
| worker | B |
| worker_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| filesystem | /dev/vdc on / (ext4) |
| workspace | /agent/repos/kosedge |
| branch | cursor/nfl-owned-market-v1-79df |
| start_tip | 9ce485e969cc57a495eff4a4038e1e2132128bec |
| written_utc | 2026-11-03T17:04:21Z |
| written_est | 2026-11-03T12:04:21-0500 |
| hard_end | 17:00 EST / 22:00 UTC |
| cos_disk_1 | HELD · no Cos-host work · no Cos staging |

## `df -h` (this Cursor worker host only)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

`findmnt -T /agent/repos/kosedge`: SOURCE `/dev/vdc` TARGET `/` FSTYPE ext4 SIZE 253.3G AVAIL 245.3G.

| path | free bytes | free GiB | threshold | result |
|---|---|---|---|---|
| /agent/repos/kosedge | 263417479168 | 245.326645 | 15 GiB | PASS |
| /tmp | 263417479168 | 245.326645 | 15 GiB | PASS |
| / | 263417479168 | 245.326645 | 15 GiB | PASS |

**GATE 0: PASS** (245.326645 GiB free on `/dev/vdc`). Restore/coding may resume on this host only.

## Preserve

- Cos ACCEPT ff45970b @ tip 9ce485e9 (risk1 ATS/ROI/CLV + profile separation + no outcome join)
- owned_completion_claimed=false
- No 2022/23 quote values, no API/DB/broad scan, no invented clock/missingness causes
