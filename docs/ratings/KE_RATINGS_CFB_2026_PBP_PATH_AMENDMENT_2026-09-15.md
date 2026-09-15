# Amendment to #556 — CFB current-season PBP path (2026-09-15)

**Amends:** [`docs/ratings/KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md`](KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md) (PR #556)  
**Evidence:** [CFB 2026 current-season PBP proof](../cfb/CFB_2026_CURRENT_SEASON_PBP_PROOF_2026-09-15.md) · PR #555 raw-metric definitions  
**Lock:** CFBD soft-parked. No ratings build. No opponent adjustment. No Edge Board / KEI.

This note **does not rewrite** the #556 inventory body or the Aug 13 2014–2025 warehouse inventories. It updates **gap implications** only.

---

## What #555 / #556 said (still true unless crossed out)

| Claim | Status after this proof |
| --- | --- |
| No module named KE Ratings Engine | Unchanged |
| CFB live compose/KEI is 2025 SP+ carry + synthetic success/pace/explosiveness | Unchanged — **not** switched to PBP |
| Owned PBP EPA warehouse is research-only (`used_in_spread: false`) | Unchanged |
| 2025 CFB PBP was not opened by #556 | Unchanged |
| **2026 current-season form = NEED_EXTERNAL because 2026 PBP was absent and CFBD auth was the live option** | **Superseded for retrieval** |
| PPA required CFBD `/ppa` | Still true **if** PPA is mandatory; PPA is optional |
| Havoc-as-published / ST need charted or verified flags | Unchanged (boolean `havoc` is unverified) |
| Opponent-adjusted KE ratings are separate work | Unchanged |

---

## What changed: current-season PBP is SDV, not CFBD-blocked

2026 `espn_cfb_pbp` season parquet retrieved **without a CFBD key** (20,118 plays / 179 games / weeks 1–2 / 498 cols). Schedule reconcile: **84/84 `STATUS_FINAL` games are in PBP**. ESPN core plays works for a sample game; site summary 403s from this VM.

CFBD authentication is **not** the blocker for 2026 play-level EPA / success / pace / explosiveness / down splits / scoring-opportunity inputs. Soft-park CFBD. Do not buy a replacement vendor.

---

## 2026 W−1 — NEED_EXTERNAL vs OWNED_DERIVABLE

Assume a versioned current-season file on  
`/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/`  
(this VM: `data/cfb/research/pbp_current/as_of_YYYYMMDD/`).  
Filter: `season=2026` and (`week < W` **and** schedule `STATUS_FINAL`). Do not use IN_PROGRESS PBP as completed form — 95 PBP games are still non-FINAL on the SDV schedule snapshot.

| Feature (2026 through W−1) | Class | Why |
| --- | --- | --- |
| Off/def EPA (raw, unadjusted) | **OWNED_DERIVABLE** | `EPA` present, null 0 |
| Success rate (`EPA_success` / standard SR) | **OWNED_DERIVABLE** | columns + down/distance/yards |
| Pace / competitive pace | **OWNED_DERIVABLE** | `scrimmage_play`, `pos_score_diff` |
| Explosiveness (EPA≥1 or yards≥15, pass/rush) | **OWNED_DERIVABLE** | same #555 knobs |
| Early / standard / passing-down efficiency | **OWNED_DERIVABLE** | `down`, `distance` |
| Scoring opportunities / finishing inputs | **OWNED_DERIVABLE** | `drive.id`, `start.yardsToEndzone`, `type.text` |
| Field position / drive EPA inputs | **OWNED_DERIVABLE** | same |
| Rolling form W−1 from those raw metrics | **OWNED_DERIVABLE** | once FINAL + `week < W` gate is applied |
| PPA | **NEED_EXTERNAL** (optional) | not in SDV; CFBD parked — build around EPA |
| Havoc-as-published (PBU-inclusive) | **NEED_EXTERNAL** | SDV `havoc`/`TFL`/`sack`/`int` exist; **field verification later** |
| Special teams rating | **NEED_EXTERNAL** | not verified |
| Opponent-adjusted EPA / KE Ratings / SOS | **NEED_EXTERNAL** (separate work) | not started; not authorized here |
| Live compose / KEI / Edge Board / fair line | **not in this path** | still SP+ carry + proxies |

Headline for #556’s CFB “EPA / PPA = PARTIAL” cell: **raw 2026 EPA is now retrievable on the owned SDV path.** That does **not** promote warehouse EPA onto KEI and does **not** raise the ~28% proprietary KE Ratings estimate. Live CFB efficiency remains vendor SP+.

---

## Preserve historical

Do not copy 2026 into `/Volumes/KosEdgeData/raw/cfb/pbp/`.  
Do not edit `data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json` as if 2026 replaced 2021–2025.

**STOP.**
