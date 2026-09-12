# CFB Data Layer v2 — HIGH_ENV information sufficiency

**Generated:** `2026-09-12T22:31:11Z`
**Production MATCHUP_RESPONSE:** `1.4` (unchanged)
**Kill switch:** `OFF`  **#532:** DO NOT MERGE
**Scoring equation:** frozen  **Lake mounted:** `True`

Target locked: `actual_total >= 68` (threshold 68.0). Capture target: `None`.
Frozen splits unchanged: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.
2025 sealed. 2026 not in the loss. Actual totals are the labels. Close is diagnostic.
α / A1 / E3 / C2 were not retuned. No scoring-model fitting. No threshold shopping.

## Decision

**STABLE_SIGNAL_CANDIDATE_FOR_ARCHITECTURE_V2**

Ship: **false**. Winner: **none**. PLAY: **false**.

At least one v2 family ranks HIGH_ENV better than chance in the same direction on Train-0, Val-0, and Val-1. Still not a production model. Architecture v2 may be designed from these families.

Stable features: `['curr_sum_def_epa', 'curr_sum_explosive_allowed', 'curr_sum_pace_plays', 'curr_two_explosive', 'curr_mean_game_total', 'curr_high_env_rate', 'prior_sum_def_epa', 'prior_sum_explosive_created', 'prior_sum_explosive_allowed', 'prior_sum_pace', 'prior_mean_game_total', 'prior_high_env_rate', 'rank_avg_v2_env']`
Stable families: `['curr_env', 'curr_epa', 'curr_explosive', 'curr_interaction', 'curr_pace', 'predeclared_composite', 'prior_env', 'prior_epa', 'prior_explosive', 'prior_pace']`
New PBP families that cleared: `['curr_sum_def_epa', 'curr_sum_explosive_allowed', 'curr_sum_pace_plays', 'curr_two_explosive', 'prior_sum_def_epa', 'prior_sum_explosive_created', 'prior_sum_explosive_allowed', 'prior_sum_pace']`

## What was asked

Not another coefficient. Not a 40–60% capture hunt.

Build a point-in-time-safe feature layer that can represent scoring environment, then rerun the frozen HIGH_ENV ≥68 protocol on Train-0 / Val-0 / Val-1. Let the data say how predictable this tail is.

Val-1: 140 / 717 = 19.5%. Those games averaged 79.221. The rest averaged 47.555.

Stability gate (predeclared, not shopped): AUC ≥ 0.55 **and** top-decile HIGH_ENV rate > prevalence on **all three** windows.

## Source inventory

Raw SportsDataverse PBP on `/Volumes/KosEdgeData/raw/cfb/pbp/` for 2021–2024 only. 2021 is prior-year for Train-0. The 2025 parquet is on disk and was not opened.

| season | plays | team-games | EPA_explosive hits | havoc hits | TFL hits | sack hits | drive.result hits | missing requested cols |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2021 | 146367 | 1684 | 112934 | 112934 | 112934 | 112934 | 112570 | none |
| 2022 | 149654 | 1722 | 115279 | 115279 | 115279 | 115279 | 114895 | none |
| 2023 | 153626 | 1806 | 117584 | 117584 | 117584 | 117584 | 117116 | none |
| 2024 | 162950 | 1892 | 122890 | 122890 | 122890 | 122890 | 122609 | none |

Explosive definition: raw `EPA_explosive` boolean. No `epa>=1.0` / `yards>=15` fallback. Finishing: `drive.result` decode TD=6 / FG=3 because `drive.pts` is absent. Seconds/play uses half-clock `start/end.TimeSecsRem` with 0 < dt ≤ 45.

PIT: current `as_of_week W` uses only same-season `week < W`. Prior season always Y−1 = `True`. Opened 2025 = `False`. Close in v2 features = `False`. Missing means missing = `True`.

## Source gaps (not invented)

- **layer_b_returning_units_coaching:** Historical returning production, unit grades, and coaching flags are not in-repo. The 2026 real-roster snapshot is the wrong year and must not be back-cast. Missing, not filled with 50.
- **drive_pts:** drive.pts is not in the raw PBP. Finishing uses drive.result (TD=6, FG=3). PAT / two-point conversion points are not observed.
- **injuries_weather:** No point-in-time injury or weather series in the owned lake.
- **historical_roster_snapshots:** No week-indexed returning-production files for 2021–2024.

## Coverage by week (eligible lake games)

Current-season PBP features need ≥2 completed same-season games. Week 1 is structurally missing. Week 2 is thin.

| season-week | n | HIGH_ENV | curr both available | prior both available |
|---|---:|---:|---:|---:|
| 2022_w01 | 86 | 20 | 0 (0.0%) | 85 (98.8%) |
| 2022_w02 | 43 | 9 | 17 (39.5%) | 43 (100.0%) |
| 2022_w03 | 49 | 10 | 45 (91.8%) | 49 (100.0%) |
| 2022_w04 | 55 | 16 | 54 (98.2%) | 54 (98.2%) |
| 2022_w05 | 54 | 10 | 54 (100.0%) | 53 (98.1%) |
| 2022_w06 | 51 | 14 | 51 (100.0%) | 50 (98.0%) |
| 2022_w07 | 45 | 21 | 45 (100.0%) | 44 (97.8%) |
| 2022_w08 | 48 | 4 | 48 (100.0%) | 47 (97.9%) |
| 2022_w09 | 42 | 10 | 42 (100.0%) | 42 (100.0%) |
| 2022_w10 | 54 | 10 | 54 (100.0%) | 53 (98.1%) |
| 2022_w11 | 59 | 9 | 59 (100.0%) | 58 (98.3%) |
| 2022_w12 | 56 | 13 | 56 (100.0%) | 55 (98.2%) |
| 2022_w13 | 59 | 13 | 59 (100.0%) | 58 (98.3%) |
| 2022_w14 | 11 | 5 | 11 (100.0%) | 11 (100.0%) |
| 2023_w01 | 66 | 14 | 0 (0.0%) | 66 (100.0%) |
| 2023_w02 | 42 | 8 | 19 (45.2%) | 42 (100.0%) |
| 2023_w03 | 49 | 9 | 46 (93.9%) | 49 (100.0%) |
| 2023_w04 | 57 | 12 | 57 (100.0%) | 57 (100.0%) |
| 2023_w05 | 52 | 10 | 52 (100.0%) | 52 (100.0%) |
| 2023_w06 | 44 | 12 | 44 (100.0%) | 44 (100.0%) |
| 2023_w07 | 51 | 10 | 51 (100.0%) | 51 (100.0%) |
| 2023_w08 | 50 | 2 | 50 (100.0%) | 50 (100.0%) |
| 2023_w09 | 50 | 10 | 50 (100.0%) | 50 (100.0%) |
| 2023_w10 | 60 | 11 | 60 (100.0%) | 60 (100.0%) |
| 2023_w11 | 60 | 15 | 60 (100.0%) | 60 (100.0%) |
| 2023_w12 | 59 | 8 | 59 (100.0%) | 59 (100.0%) |
| 2023_w13 | 60 | 19 | 60 (100.0%) | 60 (100.0%) |
| 2023_w14 | 10 | 3 | 10 (100.0%) | 10 (100.0%) |
| 2024_w01 | 75 | 15 | 0 (0.0%) | 75 (100.0%) |
| 2024_w02 | 44 | 3 | 18 (40.9%) | 44 (100.0%) |
| 2024_w03 | 47 | 9 | 43 (91.5%) | 47 (100.0%) |
| 2024_w04 | 49 | 9 | 48 (98.0%) | 49 (100.0%) |
| 2024_w05 | 50 | 12 | 50 (100.0%) | 50 (100.0%) |
| 2024_w06 | 43 | 10 | 43 (100.0%) | 43 (100.0%) |
| 2024_w07 | 47 | 9 | 47 (100.0%) | 47 (100.0%) |
| 2024_w08 | 55 | 12 | 55 (100.0%) | 55 (100.0%) |
| 2024_w09 | 51 | 7 | 51 (100.0%) | 51 (100.0%) |
| 2024_w10 | 44 | 12 | 44 (100.0%) | 44 (100.0%) |
| 2024_w11 | 46 | 10 | 46 (100.0%) | 46 (100.0%) |
| 2024_w12 | 48 | 9 | 48 (100.0%) | 48 (100.0%) |
| 2024_w13 | 57 | 12 | 57 (100.0%) | 57 (100.0%) |
| 2024_w14 | 61 | 11 | 61 (100.0%) | 61 (100.0%) |

Val-1 current-both available: 85.2% (611 / 717). Prior-both: 100.0%.

## Val-1 discrimination

### v2 families

| feature | family | AUC | PR-AUC | top-decile rate | lift | capture | coverage |
|---|---|---:|---:|---:|---:|---:|---:|
| rank_avg_v2_env | predeclared_composite | 0.667 | 0.368 | 39.3% | 1.970 | 19.7% | 85.2% |
| curr_sum_def_epa | curr_epa | 0.637 | 0.320 | 37.7% | 1.888 | 18.9% | 85.2% |
| curr_mean_game_total | curr_env | 0.635 | 0.360 | 35.1% | 1.715 | 17.1% | 79.8% |
| prior_sum_def_epa | prior_epa | 0.631 | 0.302 | 37.5% | 1.921 | 19.3% | 100.0% |
| curr_sum_explosive_allowed | curr_explosive | 0.622 | 0.315 | 39.3% | 1.970 | 19.7% | 85.2% |
| curr_sum_ppp_allowed | curr_finish | 0.620 | 0.316 | 36.1% | 1.806 | 18.0% | 85.2% |
| curr_sum_finish_allowed | curr_finish | 0.613 | 0.320 | 36.1% | 1.806 | 18.0% | 85.2% |
| prior_mean_game_total | prior_env | 0.609 | 0.274 | 34.7% | 1.778 | 17.9% | 100.0% |
| curr_sum_pace_plays | curr_pace | 0.606 | 0.272 | 29.5% | 1.478 | 14.8% | 85.2% |
| curr_sum_sit_pace | curr_pace | 0.605 | 0.283 | 31.1% | 1.560 | 15.6% | 85.2% |
| curr_high_env_rate | curr_env | 0.604 | 0.335 | 40.4% | 1.973 | 19.7% | 79.8% |
| curr_sum_sack_created | curr_havoc | 0.599 | 0.288 | 31.1% | 1.560 | 15.6% | 85.2% |
| prior_sum_explosive_allowed | prior_explosive | 0.593 | 0.239 | 22.2% | 1.138 | 11.4% | 100.0% |
| curr_two_fast | curr_interaction | 0.590 | 0.264 | 34.4% | 1.724 | 17.2% | 85.2% |
| prior_high_env_rate | prior_env | 0.590 | 0.237 | 25.0% | 1.280 | 12.9% | 100.0% |
| prior_sum_pace | prior_pace | 0.578 | 0.269 | 31.9% | 1.636 | 16.4% | 100.0% |
| curr_sum_success_allowed | curr_success | 0.570 | 0.300 | 31.1% | 1.560 | 15.6% | 85.2% |
| prior_sum_explosive_created | prior_explosive | 0.564 | 0.236 | 27.8% | 1.423 | 14.3% | 100.0% |
| curr_two_explosive | curr_interaction | 0.552 | 0.247 | 32.8% | 1.642 | 16.4% | 85.2% |
| curr_sum_havoc_created | curr_havoc | 0.548 | 0.235 | 29.5% | 1.478 | 14.8% | 85.2% |
| curr_sum_explosive_pass | curr_explosive | 0.545 | 0.221 | 21.3% | 1.067 | 10.7% | 85.2% |
| sum_qb_talent | layer_a | 0.540 | 0.230 | 20.8% | 1.067 | 10.7% | 100.0% |
| curr_sum_tfl_created | curr_havoc | 0.537 | 0.224 | 27.9% | 1.396 | 13.9% | 85.2% |
| curr_sum_explosive_created | curr_explosive | 0.537 | 0.231 | 29.5% | 1.478 | 14.8% | 85.2% |

### Diagnostic / v1 reference / source gap

| feature | role | AUC | lift | capture | coverage |
|---|---|---:|---:|---:|---:|
| close_total | diagnostic | 0.664 | 1.778 | 17.9% | 100.0% |
| v1_e3_proxy | v1_reference | 0.590 | 1.494 | 15.0% | 100.0% |
| v1_sum_off_eff | v1_reference | 0.470 | 0.711 | 7.1% | 100.0% |

### Val-1 week ≥ 4 (current-season families only; n=551, HIGH_ENV=113)

| feature | AUC | lift | capture | coverage |
|---|---:|---:|---:|---:|
| rank_avg_v2_env | 0.661 | 1.947 | 19.5% | 99.8% |
| curr_sum_def_epa | 0.637 | 1.947 | 19.5% | 99.8% |
| curr_mean_game_total | 0.631 | 1.672 | 16.8% | 99.3% |
| curr_sum_explosive_allowed | 0.620 | 1.858 | 18.6% | 99.8% |
| curr_sum_ppp_allowed | 0.612 | 1.681 | 16.8% | 99.8% |
| curr_sum_finish_allowed | 0.609 | 1.770 | 17.7% | 99.8% |
| curr_sum_sack_created | 0.607 | 1.681 | 16.8% | 99.8% |
| curr_sum_pace_plays | 0.604 | 1.504 | 15.0% | 99.8% |
| curr_sum_sit_pace | 0.600 | 1.504 | 15.0% | 99.8% |
| curr_high_env_rate | 0.596 | 1.936 | 19.5% | 99.3% |
| curr_two_fast | 0.585 | 1.593 | 15.9% | 99.8% |
| curr_sum_success_allowed | 0.560 | 1.504 | 15.0% | 99.8% |
| curr_sum_explosive_pass | 0.560 | 1.150 | 11.5% | 99.8% |
| curr_two_explosive | 0.550 | 1.770 | 17.7% | 99.8% |
| curr_sum_explosive_created | 0.545 | 1.593 | 15.9% | 99.8% |
| curr_sum_havoc_created | 0.542 | 1.593 | 15.9% | 99.8% |

## Stability across splits

| feature | Train-0 AUC / lift / cov | Val-0 AUC / lift / cov | Val-1 AUC / lift / capture |
|---|---|---|---|
| curr_sum_off_epa | 0.629 / 1.886 / 83.6% | 0.607 / 1.783 / 87.0% | 0.500 / 0.985 / 9.8% |
| curr_sum_def_epa | 0.581 / 1.451 / 83.6% | 0.601 / 1.054 / 87.0% | 0.637 / 1.888 / 18.9% |
| curr_sum_explosive_allowed | 0.622 / 1.741 / 83.6% | 0.600 / 1.540 / 87.0% | 0.622 / 1.970 / 19.7% |
| curr_sum_pace_plays | 0.572 / 1.161 / 83.6% | 0.606 / 1.621 / 87.0% | 0.606 / 1.478 / 14.8% |
| curr_mean_sec_per_play | 0.667 / — / 0.7% | — / — / 0.0% | 0.857 / — / — |
| curr_sum_finish | 0.616 / 1.524 / 83.6% | 0.576 / 1.783 / 87.0% | 0.485 / 0.985 / 9.8% |
| curr_sum_ppp | 0.627 / 1.814 / 83.6% | 0.583 / 1.702 / 87.0% | 0.492 / 1.149 / 11.5% |
| curr_sum_havoc_created | 0.504 / 1.161 / 83.6% | 0.482 / 0.891 / 87.0% | 0.548 / 1.478 / 14.8% |
| curr_sum_success_allowed | 0.588 / 1.741 / 83.6% | 0.534 / 0.891 / 87.0% | 0.570 / 1.560 / 15.6% |
| curr_mean_game_total | 0.681 / 1.618 / 80.2% | 0.635 / 2.341 / 82.7% | 0.635 / 1.715 / 17.1% |
| prior_mean_game_total | 0.637 / 1.486 / 98.6% | 0.602 / 2.028 / 100.0% | 0.609 / 1.778 / 17.9% |
| prior_sum_def_epa | 0.581 / 1.610 / 98.6% | 0.594 / 1.399 / 100.0% | 0.631 / 1.921 / 19.3% |
| rank_avg_v2_env | 0.697 / 1.721 / 84.0% | 0.680 / 2.107 / 87.0% | 0.667 / 1.970 / 19.7% |
| v1_sum_off_eff | 0.539 / 1.651 / 100.0% | 0.527 / 1.189 / 100.0% | 0.470 / 0.711 / 7.1% |
| v1_e3_proxy | 0.613 / 1.773 / 100.0% | 0.584 / 1.678 / 100.0% | 0.590 / 1.494 / 15.0% |
| close_total | 0.713 / 2.018 / 100.0% | 0.677 / 2.098 / 100.0% | 0.664 / 1.778 / 17.9% |
| layer_b_returning | — / — / 0.0% | — / — / 0.0% | — / — / — |

Predeclared gate cleared by: `['curr_sum_def_epa', 'curr_sum_explosive_allowed', 'curr_sum_pace_plays', 'curr_two_explosive', 'curr_mean_game_total', 'curr_high_env_rate', 'prior_sum_def_epa', 'prior_sum_explosive_created', 'prior_sum_explosive_allowed', 'prior_sum_pace', 'prior_mean_game_total', 'prior_high_env_rate', 'rank_avg_v2_env']`.

## Rank-average composite (predeclared, not fitted)

Equal-weight average of within-split percentile ranks of `curr_sum_off_epa`, `curr_sum_def_epa`, `curr_sum_explosive_allowed`, `curr_sum_pace_plays`, `curr_mean_game_total`, `prior_mean_game_total`. Needs ≥2 present members. Not a fit. No capture target.

Val-1 AUC `0.667`  top-decile rate `39.3%`  lift `1.970`  capture `19.7%`  coverage `85.2%`

| decile (1=lowest) | n | HIGH_ENV n | rate | lift |
|---:|---:|---:|---:|---:|
| 1 | 61 | 3 | 4.9% | 0.246 |
| 2 | 61 | 7 | 11.5% | 0.575 |
| 3 | 61 | 7 | 11.5% | 0.575 |
| 4 | 61 | 8 | 13.1% | 0.657 |
| 5 | 62 | 15 | 24.2% | 1.212 |
| 6 | 61 | 10 | 16.4% | 0.821 |
| 7 | 61 | 14 | 23.0% | 1.149 |
| 8 | 61 | 20 | 32.8% | 1.642 |
| 9 | 61 | 14 | 23.0% | 1.149 |
| 10 | 61 | 24 | 39.3% | 1.970 |

## Reading

The predeclared three-window gate fired. New PBP families cleared, not only the already-known schedule environment columns. The scoring equation stayed frozen. The 40–60% capture number from the v1 fork was not a target.

The composite ranks HIGH_ENV at AUC `0.697` / `0.680` / `0.667` — matching the close (`0.713` / `0.677` / `0.664`) without using it. Val-1 top-decile capture is still `19.7%` of the 140 shootouts. The tail is rankable. It is not isolatable. No 40% pocket appeared.

What is stable across Train-0 / Val-0 / Val-1:

- Defensive EPA allowed (current and prior-year).
- Explosive-play rate allowed (current and prior-year), from the raw `EPA_explosive` flag.
- True pace as plays/game (current and prior-year).
- Team scoring-environment history (current week < W, and prior-year).

What is not:

- Offense still dies out of sample. `curr_sum_off_epa` Val-1 AUC is `0.500` — the same diagnosis as v1 `sum_off_eff`. Finishing created / PPP created fail Val-1 with them.
- Havoc / TFL / sack do not clear all three windows.
- Layer B remains a source gap (coverage `0.0%`). Missing, not filled with 50.
- `curr_mean_sec_per_play` is a coverage mirage (`1.1%` present). The clock columns exist; usable 0 < dt ≤ 45 play durations almost never survive. Not a signal.

Architecture v2 may now be designed from the stable families. This pass does not design it, does not pick a winner, and does not write a coefficient.

## What this is not

- Not a production change.
- Not a new MATCHUP_RESPONSE, α, A1, E3, or C2.
- Not permission to open 2025 or turn the board on.
- Not a market-fitted totals model.
- Not a feature search after seeing Val-1. The list was predeclared.
- Not a 40–60% capture optimization.
- Not scoring architecture v2. That is the next design step, not this merge.

