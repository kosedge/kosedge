# START_PREFLIGHT_IDENTITY81759_B

CERT=0. OWNER IDENTITY 81759 t5329u under EVIDENCE 70648 / CLEAR 86257.
Capacity gate BEFORE any use of staged identities. Cos-host PAUSED.

| field | value |
|---|---|
| identity | 81759 |
| evidence | 70648 |
| ticket | t5329u |
| owner_clear | 86257 |
| worker | B |
| worker_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| filesystem | /dev/vdc on / (ext4) |
| workspace | /agent/repos/kosedge |
| branch | cursor/nfl-owned-market-v1-79df |
| local_head_at_gate0 | 98ec5d8618ec71be407b05e65764efeff5b259c0 |
| required_codex_commit | 8c0a04fb31b20b7964ba71f7d079ed4c60c02e5a |
| written_utc | 2026-11-03T20:33:49Z |
| written_est | 2026-11-03T15:33:49-0500 |
| hard_end | 17:00 EST / 22:00 UTC |
| cos_host | PAUSED · no Cos-host work |

## `df -h` (this Cursor worker host only)

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

| path | free bytes | free GiB | threshold | result |
|---|---|---|---|---|
| /agent/repos/kosedge | 263415287808 | 245.324604 | 15 GiB | PASS |
| /tmp | 263415287808 | 245.324604 | 15 GiB | PASS |
| / | 263415287808 | 245.324604 | 15 GiB | PASS |

**GATE 0: PASS** (245.324604 GiB free on `/dev/vdc`). Ownership: this Cursor worker (`bc-02a716be`). Cos host not used.

Staged identities were **not** on local `98ec5d86` at GATE0; fetch Codex commit `8c0a04fb` next (existing draft branch only).
