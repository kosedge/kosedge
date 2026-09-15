# Amendment to #556 — CFB current-season PBP path + classification (2026-09-15)

**Amends:** [`docs/ratings/KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md`](KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md) (PR #556)  
**Evidence:** [CFB 2026 current-season PBP proof](../cfb/CFB_2026_CURRENT_SEASON_PBP_PROOF_2026-09-15.md)  
**Full NFL+CFB matrix + first-build recommendation:** [`KE_RATINGS_NFL_CFB_GAP_MATRIX_2026-09-15.md`](KE_RATINGS_NFL_CFB_GAP_MATRIX_2026-09-15.md)  
**Lock:** CFBD soft-parked. Docs + evidence only. No ratings build. Production SP+ compose unchanged.

This note **does not rewrite** the #556 inventory body or the Aug 13 2014–2025 warehouse inventories.

**Proprietary KE Ratings estimate stays ~28%.** Inputs being on disk is not an implemented/validated rating.

---

## Classification scheme (replaces NEED_EXTERNAL dump)

Use **two axes**. Do not collapse “we have not built KE” into “we need to buy data.”

| Axis | Token | Meaning |
| --- | --- | --- |
| Data | **DATA_AVAILABLE** | Owned (or already-contracted) input exists for this concept |
| Data | **DATA_MISSING** | Input is not in owned files. Reserved for genuinely missing feeds |
| Metric | **NEEDS_IMPLEMENTATION** | Data exists; the KE metric / wiring is not built (or not on the live path) |
| Metric | **NEEDS_VALIDATION** | A field or metric exists; definition / completeness / grades are not proven |

Rules from Ryan / CoS:

- Opponent-adjusted KE = **NEEDS_IMPLEMENTATION / NEEDS_VALIDATION**, not DATA_MISSING.
- Havoc and special teams: **check field completeness first**. SDV 2026 raw has `havoc` / `TFL` / `sack` / `int` / `pass_breakup` / `forced_fumble` and kick/punt/FG columns. Those are DATA_AVAILABLE + NEEDS_VALIDATION until verification says a required input is absent.
- **PPA is optional.** Only DATA_MISSING if we insist on CFBD PPA. Default: build around EPA.
- Live CFB SP+ compose / KEI / Edge Board are **unchanged**.

---

## What changed vs the first #558 draft

| Claim | Correction |
| --- | --- |
| 84/84 completed-game coverage | **Retracted as full coverage.** 84/84 is `STATUS_FINAL`-in-snapshot ∩ PBP only |
| 2026 form = NEED_EXTERNAL (no PBP / CFBD blocked) | **Superseded for retrieval.** SDV 2026 PBP is on the versioned current path |
| Opponent-adj KE = NEED_EXTERNAL | **Wrong axis.** DATA_AVAILABLE (PBP + warehouse adj code) + NEEDS_IMPLEMENTATION / VALIDATION |
| Havoc / ST = NEED_EXTERNAL | **Premature.** Field-completeness first |
| ~28% KE Ratings | **Unchanged** |

---

## 2026 W−1 data vs metric (after refreshed reconcile)

Forced SDV schedule refresh in-cloud: **same SHA** as the first pull. All **179** PBP games sit on the schedule (0 unmatched).

| Feature (2026 through W−1) | Data | Metric | Notes |
| --- | --- | --- | --- |
| Raw EPA / success / pace / explosiveness / down splits / scoring-opp / field position | **DATA_AVAILABLE** | **NEEDS_IMPLEMENTATION** | Columns supported; completed-game rollup not built in this PR |
| Rolling form W−1 | **DATA_AVAILABLE** (85 eligible games in this snapshot) | **NEEDS_IMPLEMENTATION** | Gate: `actually_completed` ∩ PBP ∩ `week < W`. **94** live-status PBP games excluded |
| PPA | **DATA_MISSING** (optional) | n/a | CFBD parked; not required |
| Havoc-as-published | **DATA_AVAILABLE** (flags present) | **NEEDS_VALIDATION** | Verify vs published havoc before calling data missing |
| Special teams | **DATA_AVAILABLE** (play types + ST columns) | **NEEDS_VALIDATION** | Completeness / definition first |
| Opponent-adjusted KE / SOS | **DATA_AVAILABLE** | **NEEDS_IMPLEMENTATION / NEEDS_VALIDATION** | Warehouse adj exists (research, unused). Not an external-data gap |
| Live compose / KEI / Edge Board | vendor SP+ (unchanged) | not this path | Do not promote PBP onto the board here |

---

## Preserve historical

Do not copy 2026 into `/Volumes/KosEdgeData/raw/cfb/pbp/`.  
Do not edit `data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json`.

**STOP** — first bounded implementation task is specified in the matrix doc and is **not** executed here.
