# CFB P0 post-restore rematerialize

**Date:** 2026-09-11  
**PR:** https://github.com/kosedge/kosedge/pull/532  
**Tip base:** `92309a01201042748157180d6bcc99784bb35206`  
**Branch:** `cursor/cfb-name-to-code-fail-closed-6630`  
**Draft only — do not merge.** Kill switch ON. No CFB public reactivation.

Ryan CLEAR rematerialize onto #532. Structural restore only — no coefficient /
Vegas retune / threshold / PLAY publication.

## Stamp gate

| Check | Result |
|-------|--------|
| `DOCUMENTED_W2_KEI_VERSION` | `cfb-kei-v1.0-2026w2` |
| `kei_version_for_weeks((0,1,2))` | `cfb-kei-v1.0-2026w2` |
| `CFB_CLOSE_AS_OF` | `2026-09-10` |
| Pack header `kei_version` | **`cfb-kei-v1.0-2026w2`** |
| Pack header `as_of` | **`2026-09-10`** |
| Pack `generated_at` | `2026-09-11T03:41:46Z` |
| `cbb-kei` / CBB prefix | **none** (scanned written JSON) |

Week-0 per-game `apply_cfb_kei` identity remains `cfb-kei-v1.0-2026w0`.
Production mint identifier is the pack header `cfb-kei-v1.0-2026w2`.

## What ran

1. Stamp precheck (CFB namespace only).
2. `package_efficiency_2025_carry.py` against live `cfbupdate.com` **rejected** —
   TCU SP+ 8.5→3.9 / UNC −6.8→+5.8 (2026 in-season table, not final-2025).
   Frozen snapshot restored. P0 rows spliced from the year-locked ESPN
   final-2025 story using **unchanged** snapshot z-score norms
   (`--splice-p0-only`). Existing team efficiency rows bit-identical.
3. `package_real_roster_2026.py --skip-cfbd --only-codes <11 P0>` so the rest
   of the league roster pack was not rewritten. ESPN aliases: `MIZZ→MIZ`,
   `JVST→JXST`.
4. `package_power_sot_and_projections.py` — existing-team power indices
   unchanged (TCU 1.2981 / UNC 1.0633). P0 now finite.
5. `CFB_CLOSE_AS_OF=2026-09-10 python3 scripts/cfb/build_cfb_kei_futures_2026.py --kei-only`

TCU@UNC KEI stayed **−16.34 / model −15.14** (no board retune).

## MIZZ ≠ MOST

| Code | SP+ (final 2025) | Power | Conference |
|------|------------------|-------|------------|
| MIZZ | 14.4 | 1.2326 | SEC |
| MOST | −10.7 | 1.0252 | CUSA |

## 11 P0 codes — finite power (not Independent / not 1.0)

| Code | off | def | power | conference | rank |
|------|-----|-----|-------|------------|------|
| MIZZ | 1.1927 | 1.2724 | 1.2326 | SEC | 47 |
| ARST | 1.0166 | 1.0138 | 1.0152 | Sun Belt | 113 |
| CSU | 1.0279 | 1.0104 | 1.0192 | Pac-12 | 111 |
| ECU | 1.1372 | 1.1531 | 1.1452 | AAC | 70 |
| JVST | 1.1607 | 0.9528 | 1.0568 | CUSA | 95 |
| NEV | 0.9469 | 1.0130 | 0.9799 | Mountain West | 121 |
| ODU | 1.0533 | 1.0776 | 1.0654 | Sun Belt | 89 |
| TOL | 1.0881 | 1.1710 | 1.1296 | MAC | 74 |
| UAB | 1.1209 | 0.8773 | 0.9991 | AAC | 117 |
| UNM | 1.1714 | 1.1112 | 1.1413 | Mountain West | 71 |
| UNT | 1.4989 | 1.1234 | 1.3112 | AAC | 29 |

14 P0 FBS–FBS KEI games in the W0–W2 pack; none missing `kei_spread_home`.

## Artifact SHA-256

```
af5fc6f461e4c18935ecbbb0b621b90dc899cea3f8f61c2cc14f6d46bb03476d  services/model-service/src/services/cfb_season_engine/data/cfb_efficiency_snapshot_2025_carry_2026.json
69adbb61f851b4cf3ac148af85b43cdf77686a6bbef8486bf472ee6e39969cb4  services/model-service/src/services/cfb_season_engine/data/cfb_real_roster_snapshot_2026.json
5d1bf716440f14da3a554272b35f1645673093e857145aa956462b37983646d2  services/model-service/src/services/cfb_season_engine/data/cfb_fbs_team_priors_2026.json
024476e0f9ee516436d65685798d5e58e2c8fc39e5dfce1c19f7fd45b056b6eb  services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json
1412d95ca54009188fb27b44ce08c506add9787c5d38466dcaa1e38c859d1eaa  services/model-service/src/services/cfb_season_engine/data/cfb_season_projections_2026.json
dc12a178dd1681911bf665b56dc7026c69ea2b72125aa8f6d0b1d432130231c3  services/model-service/src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json
dc12a178dd1681911bf665b56dc7026c69ea2b72125aa8f6d0b1d432130231c3  apps/web/lib/data/cfb-kei-w0-w1-2026.json
4412ed8bcbaf00fde20a6c96c915378867097d367c3acda9f459ff55463a634a  apps/web/data/processed/kei_lines_cfb.json
024476e0f9ee516436d65685798d5e58e2c8fc39e5dfce1c19f7fd45b056b6eb  apps/web/lib/data/cfb-power-sot-2026.json
1412d95ca54009188fb27b44ce08c506add9787c5d38466dcaa1e38c859d1eaa  apps/web/lib/data/cfb-season-projections-2026.json
```

## Guardrails

- `CFB_EDGE_BOARD_PUBLIC_ENABLED=false`
- No PLAY / LEAN unsat
- Live cfbupdate rematerialize is **not** the 2025 carry source
