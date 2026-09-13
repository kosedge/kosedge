# CFB HIGH_ENV pregame information sufficiency

**Generated:** `2026-09-12T21:45:48Z`
**Production MATCHUP_RESPONSE:** `1.4` (unchanged)
**Kill switch:** `OFF`  **#532:** DO NOT MERGE
**Scoring equation:** frozen  **Lake mounted:** `True`

Target locked before features: `actual_total >= 68` (threshold 68.0).
Frozen splits unchanged: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.
2025 sealed. 2026 not in the loss. Actual totals are the labels. Close is diagnostic.
A1 / E3 / C2 / A3 were not retuned.

## Decision

**DATA_INSUFFICIENT_INFORMATION_EXISTS_OUTSIDE_V1**

Ship: **false**. Winner: **none**. PLAY: **false**.

v1 / owned-unused features cannot rank HIGH_ENV, but the close total can. The information exists in the world. It is not in v1.

Signal features: `[]`  Strong (≥40% capture): `[]`  Market AUC (diagnostic): `0.664`

## What was asked

Not “can we predict the exact total?” Not “can we beat the market?”

Using only information legitimately available pregame in v1 — plus unused columns already sitting in the same prior-year cache — can we rank the **140** Val-1 games that actually scored ≥68?

Val-1 prevalence is 19.5% (140 / 717). Those games averaged 79.221 points. The rest averaged 47.555.

Gates were predeclared: Val-1 AUC ≥ 0.60 and top-decile lift ≥ 2.0, with Val-0 AUC ≥ 0.57. Strong signal = top decile captures ≥ 40% of HIGH_ENV.

## Inventory: what v1 actually has

The reconstruction varies two things: prior-year adj EPA (off/def) and Layer A QB (talent / class / prior-year attempts). Everything else is a fill.

| family | in v1? | varies? |
|---|---|---|
| prior-year off/def EPA | yes | yes |
| Layer A QB talent/class | yes | yes |
| composed offense index | yes | mostly the two above |
| explosiveness / success | labeled yes | **proxy**: 50+0.15×(off−def); success=off/def |
| pace_factor | yes | almost no — units are 50 |
| returning production | filled | no (SD 0.000) |
| unit grades | filled | no (OL SD 0.000) |
| coaching changes | filled | no — all assumed returning |
| true PBP explosiveness / havoc / RZ | **absent** | — |
| opponent-adjusted current-season EPA | **absent** | — |
| unused cfb_ratings pace / FEI / ST | owned, unused | yes |
| prior-year team scoring environment | owned, unused | yes |
| current-season box before week W | owned, **not v1** | yes after W2 |

Leakage: prior season always Y−1 = `True`; opened 2025 = `False`; forbidden seasons = `[]`.

## Val-1 discrimination

### v1 + owned unused (the sufficiency question)

| feature | family | AUC | PR-AUC | top-decile rate | lift | capture | coverage |
|---|---|---:|---:|---:|---:|---:|---:|
| sum_def_susc | v1_efficiency | 0.621 | 0.292 | 43.1% | 2.205 | 22.1% | 100.0% |
| prior_mean_game_total | prior_env | 0.609 | 0.274 | 34.7% | 1.778 | 17.9% | 100.0% |
| min_def_eff | v1_efficiency | 0.608 | 0.328 | 44.4% | 2.276 | 22.9% | 100.0% |
| rank_avg_env | predeclared_composite | 0.605 | 0.298 | 37.5% | 1.921 | 19.3% | — |
| pace_factor_mean | v1_compose | 0.597 | 0.257 | 31.9% | 1.636 | 16.4% | 100.0% |
| explosiveness_sum | v1_proxy | 0.597 | 0.258 | 31.9% | 1.636 | 16.4% | 100.0% |
| a1_proxy_total | frozen_identity | 0.597 | 0.256 | 31.9% | 1.636 | 16.4% | 100.0% |
| prior_max_game_total | prior_env | 0.595 | 0.247 | 26.4% | 1.351 | 13.6% | 100.0% |
| prior_high_env_rate_mean | prior_env | 0.590 | 0.237 | 25.0% | 1.280 | 12.9% | 100.0% |
| e3_proxy_total | frozen_identity | 0.590 | 0.292 | 29.2% | 1.494 | 15.0% | 100.0% |
| product_mismatch | v1_interaction | 0.585 | 0.256 | 30.6% | 1.565 | 15.7% | 100.0% |
| prior_plays_sum | prior_box | 0.576 | 0.273 | 36.1% | 1.849 | 18.6% | 100.0% |
| prior_high_env_rate_max | prior_env | 0.576 | 0.216 | 13.9% | 0.711 | 7.1% | 100.0% |
| sum_off_pace | unused_ratings | 0.573 | 0.276 | 33.8% | 1.734 | 17.4% | 98.7% |
| prior_to_sum | prior_box | 0.566 | 0.232 | 27.8% | 1.423 | 14.3% | 100.0% |
| max_off_pace | unused_ratings | 0.555 | 0.236 | 29.6% | 1.517 | 15.2% | 98.7% |
| sum_exp_starts | v1_qb | 0.544 | 0.219 | 20.8% | 1.067 | 10.7% | 100.0% |
| pace_x_mismatch | v1_interaction | 0.544 | 0.232 | 25.4% | 1.301 | 13.0% | 98.7% |
| sum_qb_talent | v1_qb | 0.540 | 0.230 | 20.8% | 1.067 | 10.7% | 100.0% |
| max_qb_talent | v1_qb | 0.539 | 0.235 | 25.0% | 1.280 | 12.9% | 100.0% |

### Diagnostic / not-v1 / negative controls

| feature | role | AUC | lift | capture | coverage |
|---|---|---:|---:|---:|---:|
| close_total | diagnostic | 0.664 | 1.778 | 17.9% | 100.0% |
| curr_mean_game_total | current_not_v1 | 0.635 | 1.715 | 17.1% | 79.8% |
| curr_high_env_rate | current_not_v1 | 0.604 | 1.973 | 19.7% | 79.8% |
| returning_production_sum | negative_control | 0.500 | 1.067 | 10.7% | 100.0% |
| unit_ol_sum | negative_control | 0.500 | 1.067 | 10.7% | 100.0% |

### Stability across splits (selected features)

| feature | Train-0 AUC / lift | Val-0 AUC / lift | Val-1 AUC / lift / capture |
|---|---|---|---|
| e3_proxy_total | 0.613 / 1.773 | 0.584 / 1.678 | 0.590 / 1.494 / 15.0% |
| a1_proxy_total | 0.616 / 1.651 | 0.580 / 1.748 | 0.597 / 1.636 / 16.4% |
| sum_off_eff | 0.539 / 1.651 | 0.527 / 1.189 | 0.470 / 0.711 / 7.1% |
| sum_def_susc | 0.573 / 1.345 | 0.567 / 1.049 | 0.621 / 2.205 / 22.1% |
| max_off_minus_opp_def | 0.591 / 2.018 | 0.572 / 1.399 | 0.538 / 1.351 / 13.6% |
| product_mismatch | 0.608 / 1.529 | 0.586 / 1.678 | 0.585 / 1.565 / 15.7% |
| sum_off_pace | 0.551 / 1.238 | 0.581 / 1.487 | 0.573 / 1.734 / 17.4% |
| prior_mean_game_total | 0.637 / 1.486 | 0.602 / 2.028 | 0.609 / 1.778 / 17.9% |
| prior_high_env_rate_max | 0.608 / 1.300 | 0.558 / 1.608 | 0.576 / 0.711 / 7.1% |
| rank_avg_env | 0.630 / 1.345 | 0.608 / 1.818 | 0.605 / 1.921 / 19.3% |
| curr_mean_game_total | 0.681 / 1.618 | 0.635 / 2.341 | 0.635 / 1.715 / 17.1% |
| close_total | 0.713 / 2.018 | 0.677 / 2.098 | 0.664 / 1.778 / 17.9% |
| returning_production_sum | 0.500 / 0.978 | 0.500 / 1.608 | 0.500 / 1.067 / 10.7% |

## Rank-average composite (predeclared, not fitted)

Equal-weight average of within-split percentile ranks of `sum_off_eff`, `sum_def_susc`, `sum_off_pace`, `prior_mean_game_total`.

Val-1 AUC `0.605`  top-decile rate `37.5%`  lift `1.921`  capture `19.3%`

| decile (1=lowest) | n | HIGH_ENV n | rate | lift |
|---:|---:|---:|---:|---:|
| 1 | 72 | 8 | 11.1% | 0.569 |
| 2 | 71 | 9 | 12.7% | 0.649 |
| 3 | 72 | 12 | 16.7% | 0.854 |
| 4 | 72 | 13 | 18.1% | 0.925 |
| 5 | 71 | 14 | 19.7% | 1.010 |
| 6 | 72 | 14 | 19.4% | 0.996 |
| 7 | 72 | 11 | 15.3% | 0.782 |
| 8 | 72 | 18 | 25.0% | 1.280 |
| 9 | 71 | 14 | 19.7% | 1.010 |
| 10 | 72 | 27 | 37.5% | 1.921 |

## Absent families (not invented)

- **pbp_explosiveness:** cfb_ratings explosiveness is 50+0.15*(off−def), not PBP iso-explosiveness. Local PBP parquet is not mounted.
- **explosive_play_rate_allowed:** No PBP / opponent-adjusted explosive-allowed series in the v1 cache.
- **red_zone_finishing:** team_box has no red-zone attempts or TD rate.
- **havoc:** No TFL / FF / PBU / havoc rate in cfb_ratings or team_box.
- **returning_production_real:** Layer B roster is a league-average 50-fill on this reconstruction.
- **coaching_continuity_real:** Historical coaching flags are not wired; every staff is assumed returning.
- **unit_grades_real:** OL / skill / front seven / secondary are league-average 50-fills.
- **opponent_adjusted_current_season_epa:** No week-indexed adj-EPA mart. Current-season evidence, if any, is raw box only.

## Reading

The 40–60% capture fork did not fire. Nobody — v1, unused prior-year columns, current-season box, or the close — put 40% of the 140 shootouts into one decile. The closest v1 result is `sum_def_susc` / `min_def_eff` at ~22% capture. The close itself captures 18%.

**Offense does not identify the tail.** `sum_off_eff` Val-1 AUC is 0.47 — below chance in the predeclared direction. The ratio’s 54 predicted-≥68 games were high-off / low-def. Actual ≥68 games are not high-off games. That is why every scoring identity projected the real shootouts at ~55.

**Two weak defenses is the only v1 hint, and it is weak.** `sum_def_susc` Val-1 AUC 0.62 / lift 2.21 would have cleared the Val-1 gate alone, but Val-0 AUC is 0.567 (need 0.57) and Train-0 is 0.57 / lift 1.35. Not a layer. A weather vane.

**Prior-year team environment is the most stable unused column** (AUC 0.64 / 0.60 / 0.61) and still only 18% capture. Knowing that a team lived in 70-point games last year barely ranks this year’s 68+ games.

**The frozen scoring identities have no extra information.** E3 proxy AUC 0.59, A1 proxy 0.60, capture 15–16%. Changing α cannot create a tail detector that the features do not have.

**The close ranks better than v1 (AUC 0.66–0.71) and still cannot isolate shootouts.** Information exists outside this reconstruction. It is not a clean 40% pocket. Current-season box (week < W) sits between them (AUC 0.64–0.68, 80% coverage).

Negative controls are exactly 0.500. Roster/units SD is 0. Leakage checks passed. The study measured what it said it would measure.

## What this means

Do not torture α. The next work is data acquisition, not a new preseason coefficient.

Priority order suggested by the evidence, not a ship list:

1. The families the book can see that v1 cannot: true pace, in-season scoring environment, injuries, weather, explosive-play allowed, red-zone finishing.
2. Real Layer B (returning production, units, coaching) — currently 50-fills with zero variance.
3. Only after those exist, revisit a nonlinear scoring-environment layer. There is no 40% pocket to build it from today.

## What this is not

- Not a production change.
- Not a new MATCHUP_RESPONSE or α.
- Not permission to open 2025 or turn the board on.
- Not a market-fitted totals model.
- Not a feature search after seeing Val-1. The list was predeclared.

