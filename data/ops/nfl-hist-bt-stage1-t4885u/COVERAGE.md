# COVERAGE — Hist BT Stage-1 t4885u

Machine twin: `COVERAGE.json`.

## Cells

| | |
|---|---|
| Games (N) | **31** (W1=15, W2=16) |
| Required fields / game | 27 (20 efficiency + 7 context) |
| Cells | **837** |
| DERIVED_PREGAME | **277** (33.0944%) |
| MISSING_RECORD | **560** (66.9056%) |
| OUT_OF_CONTRACT | 0 |
| EXCLUDED | 0 |

## Games

| Class | N | |
|---|---|---|
| Fully reconstructable (27/27 DERIVED_PREGAME) | **0** | T1–T4 missing on every row |
| Partially reconstructable | **31** | identity + rest always; T5 on some W2 sides |

No game was dropped from the sealed sample.

## By field family

| Family | Fields | W1 (15) | W2 (16) |
|---|---|---|---|
| Identity | 5 | 75 DERIVED | 80 DERIVED |
| rest_days | 2 | 30 DERIVED | 32 DERIVED |
| T5 offense/defense index | 4 | 60 MISSING_RECORD | 60 DERIVED + 4 MISSING_RECORD |
| T1–T4 5g / matchup | 16 | 240 MISSING_RECORD | 256 MISSING_RECORD |

W2 T5 `MISSING_RECORD` sides (0 completed 2017 games as-of cutoff):

- `2017_02_CHI_TB` home **TB**
- `2017_02_MIA_LAC` away **MIA**

Both missed 2017 W1 (Irma postpone). Not filled from 2016.

## Week 1 prior-season / preseason availability

| Check | Result |
|---|---|
| 2016 REG games in `games.csv` 4fe1cdd7 | 256 (weeks 1–17); 32 teams |
| 2016 REG last-game kickoffs | present through `2017-01-01` / `2017-01-02` UTC |
| 2016 situational T1 (`nfl_dp_team_situational_weekly`) | **absent** on box |
| 2016 rolling 5g / matchup features | **absent** (rolling materialize 2023–2026 only) |
| 2016 packaged / preseason efficiency prior usable as T5/T1 | **absent**; contract §5 forbids prior substitution |
| 2017 `LAC` vs 2016 `SD` | franchise rename recorded; **not** applied as a fill |
| Week 1 handling | **MISSING_RECORD** for T5 and T1–T4. Schedule presence ≠ authorized baseline. Later-2017 not used. Sample not changed. |

## What “present” means

A field is present only when a finite value was reconstructed from an as-of-legal source under a listed transform. Empty-record `0-0 → 0.90/0.92`, dataclass defaults (`1.0` / `0.0` / `0.57` / `0.44`), hardcoded `rest_days=7.0` in `games.csv`, and 2025/2026 panels are not “present.”

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
