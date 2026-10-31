# COVERAGE — Hist BT Stage-1b t4893u (2017 REG W2 first)

Machine twin: `COVERAGE.json`.

## Sample funnel

| | |
|---|---|
| Source W2 games (`games.csv` 4fe1cdd7) | **16** |
| Excluded (0 completed same-season games as-of kickoff) | **2** |
| Eligible (sealed) | **14** |

### Exclusions (complete list)

| game_id | reason |
|---|---|
| `2017_02_CHI_TB` | TB home — 0 completed 2017 games as-of kickoff (Irma postpone). Pre-declared. |
| `2017_02_MIA_LAC` | MIA away — 0 completed 2017 games as-of kickoff (Irma postpone). Pre-declared. |

No other W2 game failed the rule. Those two games are **not** in the sealed sample and were not filled.

## Cells (eligible sample)

| | |
|---|---|
| Games (N) | **14** |
| Required fields / game | 27 (20 efficiency + 7 context) |
| Cells | **378** |
| DERIVED_PREGAME | **378** (100%) |
| MISSING_RECORD | **0** |
| OUT_OF_CONTRACT | 0 |
| EXCLUDED cells | 0 |

## Complete-game coverage (OWNER acceptance item)

| Class | N | |
|---|---|---|
| Complete eligible (27/27 DERIVED_PREGAME) | **14** | all required fields finite; source sha + cutoff on every cell |
| Partial eligible | **0** | — |

Complete game_ids: `2017_02_ARI_IND`, `2017_02_BUF_CAR`, `2017_02_CLE_BAL`, `2017_02_DAL_DEN`, `2017_02_DET_NYG`, `2017_02_GB_ATL`, `2017_02_HOU_CIN`, `2017_02_MIN_PIT`, `2017_02_NE_NO`, `2017_02_NYJ_OAK`, `2017_02_PHI_KC`, `2017_02_SF_SEA`, `2017_02_TEN_JAX`, `2017_02_WAS_LA`.

## By field family (eligible 14)

| Family | Fields | Status |
|---|---|---|
| Identity | 5 | 70 DERIVED |
| rest_days | 2 | 28 DERIVED |
| T5 offense/defense index | 4 | 56 DERIVED |
| T1–T4 5g / matchup (incl. pressure + RZ) | 16 | 224 DERIVED |

## T1 intermediate

30 team-week rows for 2017 REG W1 (`t1_team_week_2017_w1.csv`). TB and MIA have no W1 row (Irma). Those teams appear only in the excluded games.

## What “present” means

A field is present only when a finite value was reconstructed from an as-of-legal source under a listed transform. Dataclass defaults (`1.0` / `0.0` / `0.57` / `0.44`), hardcoded `rest_days=7.0` in `games.csv`, empty-record `0-0 → 0.90/0.92`, and 2025/2026 panels are not “present.”

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
