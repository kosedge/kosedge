# REPORT — t4770u H-IFT-1 2026 in-season efficiency recovery

Filed 2026-10-30 UTC · Cursor · DECISION `751dd63c` · Alex contract **v2** sha8 `b41f4b43` · IMV **PASS_CONTRACT** `1a53bbd3` (D1 CLOSED) · parent v1 `24600552` untouched · Ryan add-on t4776u

Bind: `BOUND_TO_V2_PASS_CONTRACT_1a53bbd3`. PASS_CONTRACT ≠ DATA ACCEPT ≠ emit.

## Outcome

**DATA_PARTIAL**

Through-W7 is complete and IF-consumable. Through-W8 is **not** declared complete. Incomplete W8 fails closed. E1 stays FAIL_CLOSED for scoring-admissible emit.

| Gate | Result |
|---|---|
| W1–W7 vs canonical schedule d88ae734 | 107/107 COMPLETE |
| W8 | 1/14 COMPLETE (`2026-W08-CAR@GB` TNF). 13 NOT_YET_KICKED |
| T5 `team_strength_from_record` | 32/32 from 2026 W-L through W7 |
| Contract 20/20 + v2 catch-all | 15/15 diagnostic rows; outside `NflGameInputs` fields None |
| IMV D1 | **CLOSED** — PASS_CONTRACT `1a53bbd3` on v2 `b41f4b43` |
| 2025 prior substitute | none |
| Week-9 rolling consumed | none (`rolling_as_of_week=7`) |
| IF consume @1b39f4e9 `market_blend=0` | 15/15 diagnostic (not emit) |
| t4776u 20-field IF-path consumption | 20/20 — call graph + input-hash perturbation |
| DATABASE_URL / C10 | unused |
| O4 scoring-admissible | **NO** |

## Exact W8 missing set (as_of 2026-10-30)

Do not invent. Do not backfill with 2025 priors.

1. `2026-W08-ARI@DAL` 2026-11-01T18:00:00Z NOT_YET_KICKED
2. `2026-W08-ATL@TB` 2026-11-01T18:00:00Z NOT_YET_KICKED
3. `2026-W08-BAL@BUF` 2026-11-01T18:00:00Z NOT_YET_KICKED
4. `2026-W08-CHI@SEA` 2026-11-03T01:15:00Z NOT_YET_KICKED (MNF)
5. `2026-W08-CLE@PIT` 2026-11-01T18:00:00Z NOT_YET_KICKED
6. `2026-W08-IND@JAX` 2026-11-01T18:00:00Z NOT_YET_KICKED
7. `2026-W08-KC@DEN` 2026-11-01T21:25:00Z NOT_YET_KICKED
8. `2026-W08-LAC@LAR` 2026-11-01T21:05:00Z NOT_YET_KICKED
9. `2026-W08-LV@NYJ` 2026-11-01T18:00:00Z NOT_YET_KICKED
10. `2026-W08-MIN@DET` 2026-11-01T18:00:00Z NOT_YET_KICKED
11. `2026-W08-NE@MIA` 2026-11-01T21:25:00Z NOT_YET_KICKED
12. `2026-W08-PHI@WAS` 2026-11-02T01:20:00Z NOT_YET_KICKED
13. `2026-W08-TEN@CIN` 2026-11-01T18:00:00Z NOT_YET_KICKED

TNF `2026-W08-CAR@GB` is complete in source and is **not** folded into a through-W8 label.

## Inventory (preferred no-cost / already-approved)

| Source | Finding |
|---|---|
| Packaged backbone / epa_priors 2026 | EV 2025 priors as_of 2026-08-08. Forbidden for E1. Not used. |
| Canonical schedule 2026 | EV. sha `d88ae734`. Used for expected W1–W9 set. |
| t4696u S1 restage | CLEARed URL template 2012–2022 only. 2026 not in that restage. Same URL used here. |
| t4139u W7 / t4166u W4–W6 | Referenced by CoS. No artifact on deploy-vercel, Slack, Notion, or this VM. |
| DATA_ASSETS / registers | No verified 2026 in-season efficiency asset (E1 ebfcd85b). |
| DATABASE_URL / Railway C10 | HOLD. Not used. |
| nflverse `play_by_play_2026.parquet` | Approved no-cost. sha256 `b790f399…`. 8,068,642 bytes. Public HTTPS. |

## Contract bind — PASS_CONTRACT on file; DATA still PARTIAL

Alex **v2** sha8 `b41f4b43` (parent v1 `24600552` untouched). IMV PASS_CONTRACT `1a53bbd3` closed D1 (travel_* / info_velocity_* / hours_since_change_* plus catch-all: any `NflGameInputs` field outside the 20 required + context must be None).

PASS_CONTRACT is the operative acceptance bar for this packet. It is **not** DATA ACCEPT and does **not** authorize emit.

Honest inventory outcome remains **DATA_PARTIAL** because W8 is incomplete (fail closed).

Staged W9 consume pack carries the 20 REQUIRED efficiency fields as a diagnostic. T1–T5 are existing transforms. Silent dataclass defaults are gated (ROW REJECT). Catch-all outside fields are None and recorded from the live `NflGameInputs` dataclass. Rest days from `rest_days_from_schedule`. T5 is W-L through W7 only until W8 is final.

15/15 rows ACCEPT on the **diagnostic** through-W7 panel. Week is still **not** scoring-admissible because through-W8 is incomplete.

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

**Do not retry E1 scoring-admissible emit on this DATA_PARTIAL set.**

Retry only after all of:

1. W8 final, including MNF `2026-W08-CHI@SEA` (kickoff 2026-11-03T01:15:00Z).
2. Re-fetch the same approved nflverse URL; builder reports `through_w8_complete=true`, 14/14 W8 games final in T1, 32/32 T5 records through W8.
3. IMV ACCEPT of the through-W8 DATA_* packet against v2 `b41f4b43` (PASS_CONTRACT `1a53bbd3` is already on file; it is not this ACCEPT).
4. Existing paper `ec343df3` gates still PASS.
5. New CoS CLEAR for emit (this recovery does **not** authorize emit).
6. Emit inside Tue 2026-11-03 00:00 – Wed 2026-11-04 23:59 America/New_York, with `as_of_ts ≤ emit_ts`.

If W8 PBP is not final before the window closes, slip to W10 (Nov 10–11 ET) under the same contract with W1–W9.

Do not: restore C10; substitute 2025 priors; open Odds/E2; change #662 merge status; CERT; Coming Soon OFF.

## Locks (unchanged)

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · Odds HOLD `70c56700` · overlays OFF
