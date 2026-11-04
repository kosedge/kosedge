# START_PREFLIGHT_INTEGRATE_12C41587_A

OWNER Cos ACCEPT B tip `12c41587` · RETURN 58427 + ADDITIVE 80649
Alongside RETURN 69538 / HISTORY 47316. ACK≠START.
Worker A · Cursor host only · Cos-host unused

Written 2026-11-04T00:41:05Z **before integrate work**.

## 1. Disk

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/vdc        254G  8.0G  246G   4% /
```

Available `263404630016` bytes = **245.32 GiB** ≥15. Cos `/dev/vdb` unused.

**PASS**

## 2. Ownership

- hostname: `cursor` · worker `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8`
- branch: `cursor/r7-correctness-v1-abb8` · PR #716 DRAFT
- Cos host: NOT USED

**PASS**

## 3. Head / B tip

- HEAD at GATE0: `5c0ac48af1512a25938c51692ec9cf8915a63a5a` (RETURN 69538 engine present)
- B tip `12c4158707304d1640158bfe59171237be8aca2c` present
- `a807af22` is ancestor of `12c41587` — SUPERSEDED for final integrate
- `d0bb6bef` remains refused

**PASS**

## 4. Temp-write

- created: `data/ops/nfl_ntbb_k_v1/.gate0_int12c41587.tmp`
- sha256: `175632cddabd7fefbef4d21e40bef9f1e8092a0dc7ed17e69029e40a21f7b7e0`
- deleted: yes

**PASS**

## Verdict

**GATE0 PASS.** Integrate isolated NTBB-K from `12c41587` ONCE (producer→capability/gate). Do not freeze `a807af22`. Do not promote 143 clocks. Continue 69538. CERT=0.
