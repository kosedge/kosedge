# t4643u BOUNDED REPAIR — G1–G4 only (IMV 062197c0)

DRAFT #645. No merge/deploy/Odds/F2/CERT. Stop for CoS ACCEPT → IMV grade.

## G1 `current_weekly_depth_db` — GAP (C3)

**Now:** warehouse access CLOSED (`675e1cf7` / probe `f50ba2f0`). Forecast never SELECTs `nfl_dp_*`.

**Repair:** none this ticket. Keep GAP. Completeness probe stays a separate RO tool.

**Needs CLEAR:** any SELECT into emit/sim, any SoT change. Authority tests in `WAREHOUSE_AUTHORITY.md` must pass first (flat 2907/week; injuries max_week=3). Wire-because-available = C3 RETURN.

**Contract:** `T-G1-NO-SELECT`

## G2 `depth_sot` — READ+GATE · GAP_SIM_VOLUME (C5)

**Now:** parquet read + as_of gate + pack write. Rows do not reach `NflGameInputs`. Volume = EPA.

**Repair this ticket:** labels only. Stay `PROVENANCE_ONLY`. Do not summarize as CONSUMED.

**After ACCEPT (design, still draft):** if volume is added, consume research W8 pack (`550e1a8d`), not warehouse, and add C1 fixture (change one depth row → declared volume component; EPA indices unchanged).

**Needs CLEAR:** season pack retirement W1→W8; warehouse depth as SoT.

**Contract:** `T-G2-NO-VOLUME`
**C2 oracles this tip:** sealed restore `depth_role=provenance_only` · no depth fields on `NflGameInputs`.

## G3 W8 official injury — MISSING (C2)

**Now:** 14/14 flag `w8_official_injury_report` + `injury_as_of_week8`. Overlay = last designated week (mostly 7; BUF/JAX/LAC/WAS 6; CIN 5). Empty W8 stubs unused.

**Repair this ticket:** do not invent. Keep flags.

**After ACCEPT (R1, draft builder only):** pass documented `injury_nowcast_confidence_*` when designations exist so C1 mean-effect can PASS for the overlay. Mapping named `research_designated_overlay_v1`. W8 official remains MISSING.

**Needs CLEAR:** publish / CERT of W7 overlay.

**Contract:** `T-G3-NO-INVENT` · `T-C1-INJ-FIELD`
**C2 oracles this tip:** `C2_g3_last_designated.json` · `C2_sealed_restore_oracle.json` (14/14 flags).

## G4 Season vs game SoT (C6b)

**Now:** season binds W1 depth + 2025 prior (or rolling). Game research binds W8/W7 nflverse + canonical kickoffs.

**Repair this ticket:** **DEFER + Needs-CLEAR**. Flag conflicts. Do not rewrite `_PACKAGED_DEPTH_FILES` or prior backbone.

**Contract:** `T-G4-SOT-FLAGS`
**C2/C6 oracle:** `test_c6_g4_season_still_binds_w1_and_2025_prior` (packs still bound; not rewritten).

## C4 guard

No builder change in this land that drops EPA, rest, or designated-impact wiring.

## C7

This plan is not MAE, CERT, invent-W8, merge, or Odds.
