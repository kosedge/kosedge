# REPORT — t4770u H-IFT-1 2026 in-season efficiency recovery

Filed 2026-10-30 UTC · Cursor · DECISION `751dd63c` · Alex contract **v2** sha8 `b41f4b43` · IMV **PASS_CONTRACT** `1a53bbd3` (D1 CLOSED) · parent v1 `24600552` untouched · Ryan add-on t4776u

Bind: `BOUND_TO_V2_PASS_CONTRACT_1a53bbd3`. PASS_CONTRACT ≠ DATA ACCEPT ≠ emit.

Through-W7 historical IMV **DATA_PARTIAL_ACCEPT** `c674da77` / tip `ba9e8426` remains on file. This report is the through-W8 lift after timer `t4770u-w8-complete-data-ready` at `2026-11-03T14:00:22Z`.

## Outcome

**DATA_READY**

Through-W8 is 14/14 final including MNF `2026-W08-CHI@SEA`. T5 is recomputed on 2026 W-L through W8. Independent Fair consumes the 20 required fields on the through-W8 panel. This is a dataset seal only. E1 stays locked for scoring-admissible emit.

| Gate | Result |
|---|---|
| W1–W7 vs canonical schedule d88ae734 | 107/107 COMPLETE |
| W8 | 14/14 COMPLETE including MNF `2026-W08-CHI@SEA` |
| T5 `team_strength_from_record` | 32/32 from 2026 W-L through W8 |
| Contract 20/20 + v2 catch-all | 15/15 diagnostic rows; outside `NflGameInputs` fields None |
| IMV D1 | **CLOSED** — PASS_CONTRACT `1a53bbd3` on v2 `b41f4b43` |
| 2025 prior substitute | none |
| Week-9 rolling consumed | none (`rolling_as_of_week<=8`) |
| IF consume @1b39f4e9 `market_blend=0` | 15/15 diagnostic (not emit) |
| t4776u 20-field IF-path consumption | 20/20 — call graph + input-hash perturbation |
| DATABASE_URL / C10 | unused |
| O4 scoring-admissible | **NO** |

## W8 complete set (as_of 2026-11-03)

Do not invent. Do not backfill with 2025 priors. Source: nflverse `play_by_play_2026.parquet` re-fetched + archived with `fetched_at_utc`.

All 14 W8 games are COMPLETE in PBP, including MNF `2026-W08-CHI@SEA`. `week8_missing=[]`.

Historical through-W7 PARTIAL missing list (TNF-only 1/14 as of 2026-10-30) is superseded. See `ACCEPT.json` / `IMV_GRADE_t4770u_DATA_PARTIAL.txt` for that grade.

## Inventory (preferred no-cost / already-approved)

| Source | Finding |
|---|---|
| Packaged backbone / epa_priors 2026 | EV 2025 priors as_of 2026-08-08. Forbidden for E1. Not used. |
| Canonical schedule 2026 | EV. sha `d88ae734`. Used for expected W1–W9 set. |
| t4696u S1 restage | CLEARed URL template 2012–2022 only. 2026 not in that restage. Same URL used here. |
| t4139u W7 / t4166u W4–W6 | Referenced by CoS. No artifact on deploy-vercel, Slack, Notion, or this VM. |
| DATA_ASSETS / registers | No verified 2026 in-season efficiency asset (E1 ebfcd85b). |
| DATABASE_URL / Railway C10 | HOLD. Not used. |
| nflverse `play_by_play_2026.parquet` | Approved no-cost. Re-fetched for DATA_READY. Public HTTPS. Archive + `fetched_at_utc` in `SOURCE_MANIFEST.json`. |

## Contract bind — PASS_CONTRACT on file; DATA_READY ≠ emit

Alex **v2** sha8 `b41f4b43` (parent v1 `24600552` untouched). IMV PASS_CONTRACT `1a53bbd3` closed D1 (travel_* / info_velocity_* / hours_since_change_* plus catch-all: any `NflGameInputs` field outside the 20 required + context must be None).

PASS_CONTRACT is the operative acceptance bar for this packet. It is **not** DATA ACCEPT and does **not** authorize emit.

Staged W9 consume pack carries the 20 REQUIRED efficiency fields as a diagnostic on the through-W8 panel. T1–T5 are existing transforms. Silent dataclass defaults are gated (ROW REJECT). Catch-all outside fields are None and recorded from the live `NflGameInputs` dataclass. Rest days from `rest_days_from_schedule`. T5 is W-L through W8.

15/15 rows ACCEPT on the **diagnostic** through-W8 panel. Week is still **not** scoring-admissible because emit is locked.

## Independent Fair consume proof (t4776u)

`scripts/nfl/prove_if_consume_2026_w09_t4770u.py` → `if_consume_proof.json` + `if_required_20_consumed.json`

- Entrypoint: `simulate_nfl_game_independent_fair` @ `1b39f4e9`
- Path: `simulate_nfl_game_independent_fair` → `simulate_nfl_game(independent_fair=True)` → `_build_matchup_adjustments` + `_build_totals_adjustments` + `compute_nfl_projection_decomposition`
- `NFL_INDEPENDENT_FAIR_PATH` remains False
- `market_blend=0` asserted
- `DATABASE_URL` unset
- 15/15 games produced `total_mu` / `margin_mu`
- **20/20 required fields** have AST reader cites on that path **and** a perturbation that changes the 20-field input hash and the IF output hash
- Presence on the dataset row is not accepted as consumption
- Label: DIAGNOSTIC. Not an E1 emit. Not O4.

## Exact E1 retry recommendation

**Do not retry E1 scoring-admissible emit on this DATA_READY set.**

DATA_READY is the dataset seal. Emit still requires a separate IMV DATA_READY ACCEPT and a CoS CLEAR. This recovery does not emit, merge #663, open E2, restore C10, or lift CERT.

Retry only after all of:

1. IMV ACCEPT of this through-W8 DATA_READY packet against v2 `b41f4b43` (PASS_CONTRACT `1a53bbd3` is already on file; it is not this ACCEPT).
2. Existing paper `ec343df3` gates still PASS.
3. New CoS CLEAR for emit (this recovery does **not** authorize emit).
4. Emit inside the separately authorized window, with `as_of_ts ≤ emit_ts`.

Do not: restore C10; substitute 2025 priors; open Odds/E2; change #662 merge status; CERT; Coming Soon OFF; merge #663.

## Locks (unchanged)

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · Odds HOLD `70c56700` · overlays OFF · #663 DRAFT ≠merge
