# D-1 erratum — design v2 C-7 scope + P-3 drop-one fixtures

**Task:** t4285u  
**Date:** 2026-10-23  
**Status:** ERRATUM ONLY. Does not reopen design review. No fit. No live apply.  
**Governs:** IMV ruling `IMV_RULING_NFL_INJURY_DESIGN_t4285u_v2` (filed 2026-10-23; box sha prefix `a3dac17a`), condition **D-1**.  
**Amends:** design v2 `/opt/cursor/artifacts/nfl-injury-single-application-design-t4285u-v2-20261023.md` sha `713ae876c5749cdbf050ade5f4a2cceb500230cc6b0d007fec66423e3c9e5273`.  
**Does not amend:** frozen v1/v2 test specs, W4/W5/W6/W8 seals, overlay defaults.

---

## 1. Line 321 — read as ANY injury path

Design v2 §5.2 line 321 currently says:

> Never: `or 0.0`; `_to_float(x, 0.0)` on any injury path; multiplier default 1.0 on the apply path; empty-aggregate `0.0` without the Q1 tag.

**Erratum (D-1 / C-7):** read that sentence as:

> Never: `or 0.0`; `_to_float(x, 0.0)` on **any injury path**; multiplier default 1.0 on **any injury path**; empty-aggregate `0.0` without the Q1 tag.

“Apply path” is not a narrower contract. The NULL contract covers every injury consumer, including:

| Path | File (audit `6e18e250`) | Forbidden fill |
|------|-------------------------|----------------|
| Empty nowcast aggregate | `nfl_injury_nowcast.py` `_aggregate_team_nowcast([])` | `impact_score: 0.0`, multipliers `1.0` |
| Nowcast fetch / merge | `fetch_nfl_injury_nowcast`, `_merge_roster_continuity_into_nowcast` | `float(x or 0.0)` / `get(..., 1.0)` on missing nowcast |
| Remat feature keys | `tasks.py` supervised `home/away/diff_injury_impact` | `or 0.0` |
| Supervised training rows | `tasks.py` `_fetch_nfl_supervised_training_rows` | `.get("impact_score", 0.0)` |
| Index scale | `tasks.py` `cur_* = prior * mult` | `or 1.0` on multipliers |
| Framework `injuries_depth` | `nfl_handicapping_framework.py` | `_to_float(x, 0.0)` / mult default `1.0` |
| Totals `injury_total_signal` | `nfl_simulator.py` `_build_totals_adjustments` | `mult or 1.0`, `impact or 0.0` |
| Simulator missing disclosure | `simulate_nfl_game` injury block | numeric 0.0 as if applied-healthy |
| Residual components | `apply_injury_residual_once` / ledger | NULL deltas coerced to 0.0 |
| Raw file map | sealed export / IMV runner | `injuries_2026` / `nflverse_injuries` / `raw_injury_report` → 0.0 |

Missing means **NULL + flag**, never a silent healthy fill. Sourced `0.0` remains legal **only** under locked Q1 (`source=nowcast_healthy_complete`, complete listing, `listing_as_of < kickoff`, pinned export sha). `diff_injury_impact` is NULL if either side is NULL. Simulator missing path disclosure stays **“no injury adjustment applied”** (null, never 0.0).

Engineering §7.1 item 1 is tested to this scope.

---

## 2. P-3 drop-one fixtures (specified)

v1 P-3 is the drop-one NULL-contract suite. A fixture starts from a **complete** payload `C` (every injury field on that path populated; not a Q1 sourced-0.0 row) and **drops exactly one** input. The dropped path must fail closed. Filling the hole with `0.0` or multiplier `1.0` fails the fixture.

Shared assertions for every fixture:

1. The dropped field is `None` (JSON `null`), not `0.0` / `1.0`.
2. `FLAG_MISSING_KOSEDGE_INJURY_NOWCAST` is present unless the remaining residual is complete **and** a pinned export sha is present (Q2). Partial units use `FLAG_INJURY_PARTIAL_<UNIT>` and `applied=false`.
3. `diff_injury_impact` is `None` if either side is `None`.
4. Game-line guards stay false: `index_scale_applied`, `injuries_depth_applied`, `totals_injury_signal_applied`, `kei_injury_applied`, `continuity_as_second_line`.
5. Published markets equal baseline (`applied: false`). Shadow adjusted values exist only in the sealed export.
6. Simulator injury block `disclosure == "no injury adjustment applied"` when any required injury input is missing.
7. Raw names `injuries_2026`, `nflverse_injuries`, `raw_injury_report` are refused (`FLAG_RAW_INJURIES_2026_REFUSED`); keys stay NULL.

### Fixture table

| Id | Drop | Start `C` | Must hold |
|----|------|-----------|-----------|
| **P3-1** | Empty nowcast aggregate (`rows=[]`) | n/a (empty is the drop) | `impact_score is None`; `offense_multiplier is None`; `defense_multiplier is None`; `confidence is None`; flag present; **not** Q1 |
| **P3-2** | Fetch with no listing rows | session returns `[]` | home and away match P3-1; game `home/away/diff` keys NULL |
| **P3-3** | `home_injury_impact` | complete home+away floats | home NULL; diff NULL; away may remain; flag or partial; no `or 0.0` |
| **P3-4** | `away_injury_impact` | complete home+away floats | away NULL; diff NULL; symmetric to P3-3 |
| **P3-5** | Either side of `diff_injury_impact` | complete triple | diff NULL whenever home or away is NULL |
| **P3-6** | Supervised training `.get("impact_score")` | team-week missing from severity map | row `home_injury_impact` / `away_injury_impact` NULL; **not** `0.0` |
| **P3-7** | One framework injury field (`impact_*` or `*_multiplier_*` or `confidence_*`) | complete `injuries_depth` inputs | `injuries_depth.available is False`; `margin_points == 0` **because skipped**, not because healthy; no `_to_float(x, 0.0)` / mult `1.0` on the dropped field |
| **P3-8** | One totals injury field | complete EPA + complete injury | `injury_total_signal` absent (EPA-only totals must not invent an injury term); no `mult or 1.0` / `impact or 0.0` |
| **P3-9** | All injury fields on `NflGameInputs` | EPA/matchup may be present | `injury_nowcast.disclosure == "no injury adjustment applied"`; `home_impact` / `away_impact` NULL; no numeric 0.0 apply |
| **P3-10** | One index-scale multiplier | complete priors + one missing mult | `index_scale_applied is False`; sim indices equal full-strength; missing mult is NULL, not `1.0` |
| **P3-11** | One residual unit (`off_home` / `def_home` / `ol_home` / away twins) | complete six-unit residual | dropped component NULL; `applied is False`; `FLAG_INJURY_PARTIAL_<UNIT>`; deltas NULL; Q4 all-or-nothing |
| **P3-12** | Multiplier default | complete payload minus one mult | remaining code path must not substitute `1.0` |
| **P3-13** | `_to_float(x, 0.0)` / `or 0.0` | complete payload minus one impact | remaining code path must not substitute `0.0` |
| **P3-14** | Raw file map | sealed export asked to read `injuries_2026` / `nflverse_injuries` / `raw_injury_report` | refuse; three keys NULL; `FLAG_RAW_INJURIES_2026_REFUSED` |

Continuity is **not** a legal fill for a dropped nowcast (Q9 folds into the residual; `continuity_as_second_line=false`). An empty listing plus roster-continuity rows still leaves game-line impact/multipliers NULL (P3-1/P3-2), with continuity recorded only as ledger metadata.

---

## 3. What this erratum does not do

- Does not change Q1–Q12, C-1..C-15, or v1 I/K/P/U/D/C/V/G gates.
- Does not flip `unlock_overlays`, `force_overlays_off`, KEI publish identity, or add a KEI beat.
- Does not authorize a fit, a 2024/2025 feature build, or a live apply.
- Does not require a v3 design or another IMV review loop (D-1: “An erratum or v3 note is enough.”).

---

*D-1 erratum to design v2 `713ae876`. Engineering §7.1 tests the fixtures above.*
