# START_PREFLIGHT_CLEAR92861_B

CERT=0. OWNER CLEAR 92861 t5335u · chief-nflgreen-followthrough-20261103.
Capacity/ownership gate BEFORE any package work. Cos-host unused/quarantined.

| field | value |
|---|---|
| clear | 92861 |
| ticket | t5335u |
| worker | B |
| worker_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| filesystem | /dev/vdc on / (ext4) |
| workspace | /agent/repos/kosedge |
| branch | cursor/nfl-owned-market-v1-79df |
| pr | 715 |
| head | 7ea9729fb5d40a1805f07eb4f63e61363259bd1c |
| head_match | **MATCH** (no drift) |
| written_utc | 2026-11-03T23:25:05Z |
| written_est | 2026-11-03T18:25:05-0500 |
| phase1_ceiling | 90 min wall from GATE0 PASS |
| cos_host | unused / quarantined |

## 1) Disk

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

`findmnt`: SOURCE `/dev/vdc` TARGET `/` FSTYPE ext4 SIZE 253.3G AVAIL 245.3G.

| path | free bytes | free GiB | ≥15 GiB |
|---|---|---|---|
| /agent/repos/kosedge | 263414943744 | 245.324284 | PASS |
| /tmp | 263414943744 | 245.324284 | PASS |

## 2) Ownership

Same-owner B `bc-02a716be` · branch `cursor/nfl-owned-market-v1-79df` · DRAFT PR #715.

## 3) Head SHA

`7ea9729fb5d40a1805f07eb4f63e61363259bd1c` **MATCH**.

## 4) Path-read

- `data/ops/nfl_owned_market_v1/` readable
- `CLOCK_LINEAGE_LEDGER_81759.json` sha256 `ce188c64f6d52c98ca76301455bf2654d30a6a59029cc5d7845944d7087bc5d7` · n_proven=23 · n_44=44 · n_hold=0 · claimed=false
- `codex_staged/CSV_PROVIDER_EVENT_IDENTITIES.json` sha256 `f03041adfb6720f2de2600f6ec8d7db410e38084fbebac303f58fcdfb9d5ced5` **MATCH** · n_events=23

## 5) Temp-write

`mktemp -d /tmp/clear92861_B.XXXXXX` → write probe → read → `rm -rf` → gone. **PASS**.

**GATE 0: PASS.** Phase 1 may start on this host only.
