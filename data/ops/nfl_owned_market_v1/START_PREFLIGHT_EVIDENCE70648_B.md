# START_PREFLIGHT_EVIDENCE70648_B

CERT=0. OWNER EVIDENCE 70648 t5324u under CLEAR 86257 / CONTINUE 69537.
Capacity gate BEFORE any use of staged metadata. Cos-host PAUSED.

| field | value |
|---|---|
| evidence | 70648 |
| continue | 69537 |
| ticket | t5324u |
| owner_clear | 86257 |
| worker | B |
| worker_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| filesystem | /dev/vdc on / (ext4) |
| workspace | /agent/repos/kosedge |
| branch | cursor/nfl-owned-market-v1-79df |
| local_head_at_gate0 | 70f6da89a47bafbc3ea3b058bc9b2ddc91817979 |
| required_start_tip | 2497a156b888c41c4e1b552ac9af325991c7c7e0 |
| written_utc | 2026-11-03T20:04:27Z |
| written_est | 2026-11-03T15:04:27-0500 |
| hard_end | 17:00 EST / 22:00 UTC |
| cos_host | PAUSED · no Cos-host work |

## `df -h` (this Cursor worker host only)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

| path | free bytes | free GiB | threshold | result |
|---|---|---|---|---|
| /agent/repos/kosedge | 263415746560 | 245.325031 | 15 GiB | PASS |
| /tmp | 263415746560 | 245.325031 | 15 GiB | PASS |
| / | 263415746560 | 245.325031 | 15 GiB | PASS |

**GATE 0: PASS** (245.325031 GiB free on `/dev/vdc`). Ownership: this Cursor worker (`bc-02a716be`). Cos host not used.

Staged metadata was **not** on local `70f6da89` at GATE0; fetch start tip `2497a156` next (permitted repo history on this host).
