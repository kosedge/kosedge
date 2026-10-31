# COVERAGE — Hist BT Stage-1b t4893u (2017 REG W3–W6)

Machine twin: `COVERAGE.json`.

## Sample funnel

| | |
|---|---|
| Source W3–W6 games (`games.csv` 4fe1cdd7) | **60** (16+16+14+14) |
| Excluded (0 completed same-season games as-of kickoff) | **0** |
| Eligible (sealed) | **60** |

### Exclusions (complete list)

None. The fixed rule was applied. Irma TB/MIA had completed W2 before W3, so they are in the sealed sample (not filled).

## Cells (eligible sample)

| | |
|---|---|
| Games (N) | **60** |
| Required fields / game | 27 (20 efficiency + 7 context) |
| Cells | **1620** |
| DERIVED_PREGAME | **1576** (97.284%) |
| MISSING_RECORD | **44** |
| OUT_OF_CONTRACT | 0 |
| EXCLUDED cells | 0 |

## Complete-game coverage (OWNER acceptance item)

| Class | N | |
|---|---|---|
| Complete eligible (27/27 DERIVED_PREGAME) | **56** | all required fields finite; source sha + cutoff on every cell |
| Partial eligible | **4** | W6 homes on W5 bye; exact rating_week T2 miss |

### By week

| Week | Eligible | Complete 27/27 | Partial |
|---|---|---|---|
| 3 | 16 | **16** | 0 |
| 4 | 16 | **16** | 0 |
| 5 | 14 | **14** | 0 |
| 6 | 14 | **10** | 4 |
| Combined | 60 | **56** | 4 |

### Partial games (complete list)

| game_id | bye side | rating_week | derived / 27 | missing |
|---|---|---|---|---|
| `2017_06_DET_NO` | NO home (W5 bye) | 5 | 16 | 11 |
| `2017_06_MIA_ATL` | ATL home (W5 bye) | 5 | 16 | 11 |
| `2017_06_SF_WAS` | WSH home (W5 bye) | 5 | 16 | 11 |
| `2017_06_NYG_DEN` | DEN home (W5 bye) | 5 | 16 | 11 |

Missing cells on each: that side’s 5 T1 5g fields + 6 T4 diffs. Identity, rest_days, T5, and the other side’s 5 T1 fields are DERIVED. No fills.

## By field family (eligible 60)

| Family | Fields | Status |
|---|---|---|
| Identity | 5 | 300 DERIVED |
| rest_days | 2 | 120 DERIVED |
| T5 offense/defense index | 4 | 240 DERIVED |
| T1–T4 5g / matchup (incl. pressure + RZ) | 16 | 916 DERIVED + 44 MISSING |

## T1 intermediate

154 team-week rows for 2017 REG W1–W5 (`t1_team_week_2017_w1w5.csv`): W1=30 (no TB/MIA), W2–W4=32, W5=28 (ATL/DEN/NO/WSH bye). W1 slice is byte-numeric-identical to the W2 packet T1 file (max abs 0).

## What “present” means

A field is present only when a finite value was reconstructed from an as-of-legal source under a listed transform. Dataclass defaults, hardcoded `rest_days=7.0` in `games.csv`, empty-record `0-0 → 0.90/0.92`, last-played-week T2, and 2025/2026 panels are not “present.”

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
