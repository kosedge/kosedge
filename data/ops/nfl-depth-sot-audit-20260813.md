# NFL Depth + Coaching SoT Audit — Go-Mode Gate A

**Date:** 2026-08-13  
**Branch:** `feat/nfl-depth-sot-audit-gomode` → `deploy-vercel`  
**Doctrine:** News → expert note → SoT pack → engine. No dual maps. No KEI. Model version unchanged.

Script: `python scripts/nfl/audit_depth_sot.py`  
Pack: `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json`  
Coaching: `…/data/nfl_coaching_staff_2026.json`  
Snapshot: `nfl-depth-2026-w1-20260813T120000Z`

## 1. Inventory — what the engine actually reads

| Artifact | Path | Who consumes it |
| --- | --- | --- |
| **Depth SoT** | `nfl_depth_chart_2026_w1.json` | `load_packaged_depth_chart` → season engine, game boxes, survivor, fantasy season totals, team intel Depth/Roster Pulse, continuity `fetch_current_qb1`, QB premium |
| **Coaching SoT** | `nfl_coaching_staff_2026.json` | `load_packaged_coaching_staff` → Team Intel staff + True PR continuity staff flags |
| Packager overrides | `scripts/nfl/package_season_engine_depth_2026.py` `SOT_QB_OVERRIDES` | Re-pack cannot resurrect Tua→MIA / Kyler→ARI |

### Alternate paths still in the repo (gated)

| Path | When it can fire | REG product |
| --- | --- | --- |
| `nfl_dp_depth_chart_weekly` | Only if **no** packaged SoT file for the season | Dead while pack exists |
| `nfl_dp_official_depth_charts` | Same | Dead while pack exists |
| `demo_depth_chart` / `_generic_skill` (`"{team} QB1"`) | Explicit `demo=True` **or** pack missing | **Blocked** when pack present (`demo_depth_fill=blocked_pack_present`). Empty team = hole, not a fake starter. |

`resolve_season_universe(demo=False)` still prefers pack; DB weekly/official identities are ignored when the pack is present (#160 contract kept).

## 2. Coverage (2026-08-13)

| Layer | Before (pack as_of 2026-08-09) | After |
| --- | ---: | ---: |
| Depth teams with named QB/RB/WR/TE1 | **32 / 32** | **32 / 32** |
| Skill rows | 383 | 383 |
| Named HC | **32 / 32** | **32 / 32** |
| HC+OC+DC | 31 / 32 | 31 / 32 |
| Thin DC (honest) | **TB** | **TB** |
| Demo fill on REG when pack present | Silent `{team} QB1` if a team hole | **Blocked** |
| Product banner | “synthetic roles until live feeds land” | Packaged SoT, named starters, not a live injury feed |

Coverage was already 32/32 **names**. The hole was **wrong-team identities** (Tua/Willis), not missing rows.

## 3. Override table

| Team | Field | Before | After | Reason | as_of |
| --- | --- | --- | --- | --- | --- |
| **ATL** | QB1 | Michael Penix Jr. | **Tua Tagovailoa** (`open_competition`) | Desk + ATL preview: Tua signed ATL in FA. Pack had him on MIA (Kyler-class dual map). Not a named crown — Penix still in the room, ACL-limited. | 2026-08-13 |
| **ATL** | QB2 | Malik Willis | **Michael Penix Jr.** (`open_competition`, limited) | Penix stays ATL. Dual unresolved. | 2026-08-13 |
| **MIA** | QB1 | Tua Tagovailoa | **Malik Willis** | MIA rebuild QB1 (preview). Willis was incorrectly ATL QB2. | 2026-08-13 |
| **MIN** | QB1 | Kyler Murray | Kyler Murray (`named_starter`) | Camp Desk 2026-08-12: O’Connell named him 2026-08-11. Identity already correct; labeled. | 2026-08-13 |
| **ARI** | QB1 | Jacoby Brissett | Jacoby Brissett | Post-move. Kyler is MIN only. | 2026-08-09 |
| **CLE** | QB1/QB2 | Watson starter / Sanders backup | Same names, **`open_competition`** | Monken has not named a starter (desk 2026-08-12). Pack order is not a crown. | 2026-08-13 |
| **CLE** | LT1 (`ol_roles`) | — | **Spencer Fano** | Desk: Fano with the ones. OL tracking SoT, not skill usage. | 2026-08-13 |
| **WAS** | WR2 / TE3 / OL | Diggs / Bates OUT / Tunsil OUT | Unchanged | Daily intel 2026-08-09 still current. | 2026-08-09 |
| **KC** | QB1 | Mahomes | Mahomes | Spot-check clean. | — |
| **SF** | QB1 | Purdy | Purdy | Spot-check clean. | — |

Packager `SOT_QB_OVERRIDES` updated so a re-pack cannot put Tua back on MIA.

## 4. Remaining open battles

| Team | Status | Honesty |
| --- | --- | --- |
| **ATL QB** | Tua vs Penix (availability) | `open_competition`. Do not invent a Week 1 lock. Cooper Rush is a camp arm — not added without a GSIS id. |
| **CLE QB** | Watson vs Sanders | `open_competition`. Preseason starts are evaluation tape. |
| **TB DC** | unnamed in coaching pack | Thin / unknown. Not invented. |
| **WAS OL** | Tunsil season OUT; Allegretti camp OUT; LG competition | `ol_roles` + KEI flag. No invented EPA. Gate B. |
| **KC OC** | Pack lists Eric Bieniemy | Not on the conflict checklist; left as curated 2026 staff. Confirm on the next staff pass if the desk disagrees. |

## 5. Code paths killed or gated

- `_generic_skill` / `{team} QB1` **no longer fills holes** when `nfl_depth_chart_2026_w1.json` is present (`loaders._ensure_team_rosters(allow_demo_fill=False)`).
- `seasonEnginePackagedNotice` no longer claims “synthetic roles until live feeds land.”
- Intel depth rows pass through pack `depth_slot` + `competition_status` (open battles stay labeled).
- `demo=True` still uses demo depth (tests only).

## 6. Propagation smoke

| Check | Result |
| --- | --- |
| MIN depth intel QB1 = engine roster QB1 = continuity QB1 | **Kyler Murray** |
| MIN scheduled game-box QB1 | **Kyler Murray** (`on_loaded_schedule`) |
| ARI game-box (existing) | Brissett (unchanged) |
| ATL/MIA exclusive | Tua only on ATL; Willis only on MIA |
| WAS Diggs / Tunsil / Bates | Still in pack |
| League finite / 32×4000 | Not re-run. **Call-out:** ATL/MIA QB identity swap is large enough to **require a republish** before treating wins/PF/usage as current. Not run in this PR (explicit non-goal unless required). |
| Model version | Unchanged (`nfl-season-engine-v1.27-kicker-layer`) |
| Edge Board / project | Untouched this pass (data SoT only) |

## 7. Tests

`services/model-service/tests/test_nfl_depth_sot_audit.py` — 32/32 named starters, conflict identities, no demo fill when pack present, MIN intel/engine/box agree, WAS/CLE OL+open battles.  
Existing `test_nfl_roster_source_of_truth.py` / `test_nfl_depth_coaching_sot.py` still apply (Kyler MIN, Brissett ARI).  
Web: `nfl-season-engine-ready.test.ts` banner copy.

## Success / next

Live NFL surfaces read **one** 2026 depth/coaching SoT. Starter sheet is auditable. Banner matches residual truth (packaged named depth, not a live injury feed).

**Gate B next:** KEI Week 1 handicap factors (injury/QB confirmation, rest/travel, weather) as reprice only. Model untouched. Republish 100k after this identity swap before quoting ATL/MIA wins.
