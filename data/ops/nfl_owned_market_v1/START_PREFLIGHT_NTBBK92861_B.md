# START_PREFLIGHT_NTBBK92861_B

CERT=0. CLEAR 92861 NTBB-K SYNTHETIC KERNEL ORDER.
Capacity/ownership gate BEFORE any kernel work. Cos-host unused/quarantined.
ACK≠START. Fresh GATE0 on THIS Cursor host.

| field | value |
|---|---|
| clear | 92861 |
| order | NTBB-K SYNTHETIC KERNEL |
| owner | 92a6ca83 |
| alex_pass_spec | 4f8c5827 |
| evidence | 03972 · t5343u |
| worker | B |
| worker_id | bc-02a716be-429a-56c8-ab0f-5f262aa479df |
| hostname | cursor |
| filesystem | /dev/vdc on / (ext4) |
| workspace | /agent/repos/kosedge |
| branch | cursor/nfl-owned-market-v1-79df |
| pr | 715 |
| head | e7084587af0a3ca74be41a534143eedce44ab521 |
| head_match | **MATCH** (no drift) |
| written_utc | 2026-11-03T23:45:08Z |
| phase1_ceiling | 120 min wall from GATE0 PASS |
| cos_host | unused / quarantined |

## 1) Disk

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

`findmnt`: SOURCE `/dev/vdc` TARGET `/` FSTYPE ext4 SIZE 253.3G AVAIL 245.3G.

| path | free bytes | free GiB | ≥15 GiB |
|---|---|---|---|
| /agent/repos/kosedge | 263413248000 | 245.322704 | PASS |
| /tmp | 263413248000 | 245.322704 | PASS |

## 2) Ownership

Same-owner B `bc-02a716be` · branch `cursor/nfl-owned-market-v1-79df` · DRAFT PR #715.

## 3) Head SHA

`e7084587af0a3ca74be41a534143eedce44ab521` **MATCH**.

## 4) Path-read (preserve market PARTIAL)

- `data/ops/nfl_owned_market_v1/` readable
- `CLOCK_LINEAGE_LEDGER_81759.json` sha256 `ce188c64f6d52c98ca76301455bf2654d30a6a59029cc5d7845944d7087bc5d7` · 23/44
- `CLOCK_LINEAGE_LEDGER_92861.json` sha256 `6879ed43cc9e4ad7bef0a124bc0514ea7d1adb9af1775101e0bbcd6aad6d5e75` · PARTIAL
- `codex_staged/CSV_PROVIDER_EVENT_IDENTITIES.json` sha256 `f03041ad…` MATCH
- `codex_staged/JSONL_SELECTED_143_SOURCE_VALUE_PROJECTION.json` sha256 `bf5fd92e61f3f0bac9f964e7b57b7ac4996ba166c68bb853888c9fcdb0e9e2d7` MATCH · SOURCE_VALUE_MATCH ≠ verified clocks

## 5) Temp-write

`mktemp -d /tmp/clear92861_NTBBK_B.XXXXXX` → write probe → read → `rm -rf` → gone. **PASS**.

**GATE 0: PASS.** Kernel work may start on this host only.
