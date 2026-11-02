# D-4 pre-fit amendment — injury residual cal v2

**Task:** t4285u  
**Date:** 2026-10-23  
**Status:** PROTOCOL AMENDMENT ONLY. **No fit has been run.** No 2024/2025 feature rows. No outcome or closing-line join.  
**Governs:** IMV ruling `IMV_RULING_NFL_INJURY_DESIGN_t4285u_v2` (box sha prefix `a3dac17a`), conditions **D-2** and **D-4**.  
**Design:** v2 sha `713ae876c5749cdbf050ade5f4a2cceb500230cc6b0d007fec66423e3c9e5273`.  
**Erratum:** D-1 sha `b0c57063f93d23a2535f9328669a649f3629e31922195fa404e13245e4d52ce8`.  
**PR:** https://github.com/kosedge/kosedge/pull/611 (DRAFT, review only; no merge; no deploy).

This file is the single hashed pre-fit amendment required before any fit. **The fit may run only after IMV acknowledges this file in writing.**

---

## 1. Code sha (full)

| Field | Value |
|-------|--------|
| Protocol id | `injury-residual-cal-v2` |
| Engineering commit (full) | `3fa9f024360efd70209b7348e6c812a588fe1c74` |
| Branch | `cursor/nfl-injury-null-contract-1a07` |
| Base | `deploy-vercel` |
| What the sha covers | §7.1 items 1–7 + P-3 drop-one tests. Overlay defaults unchanged. |

This is the executable tree the fit would compile against. A later document-only commit of **this amendment** does not change that code sha.

---

## 2. Config hash (includes `NFL_TOTALS_*`)

Computed by `nfl_injury_null_contract.config_hash` with every `NFL_TOTALS_*` **unset** (legal C-9: unset or finite). Ambient env had no `NFL_TOTALS_*` keys.

| Hash | sha256 |
|------|--------|
| Config hash (NFL_TOTALS_* + ledger identity) | `0d491abef53cb67e82106dda184fb40fbe21fc3883afd8313fd87108cf40d6cb` |
| Bound hash (same + protocol id + code sha) | `638198a551ad192180d635a8edd1406b5aa8f1f47fbb026a98332ffee09e7db5` |

**Resolved `NFL_TOTALS_*` (all unset → JSON `null`):**

```
NFL_TOTALS_CALIBRATION_HALF_LIFE_DAYS = unset
NFL_TOTALS_CALIBRATION_INTERCEPT_ABS_MAX = unset
NFL_TOTALS_CALIBRATION_INTERCEPT_DEFAULT = unset
NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS = unset
NFL_TOTALS_CALIBRATION_MAX_TOTAL = unset
NFL_TOTALS_CALIBRATION_MIN_SAMPLE = unset
NFL_TOTALS_CALIBRATION_MIN_SLATE = unset
NFL_TOTALS_CALIBRATION_MIN_TOTAL = unset
NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE = unset
NFL_TOTALS_CALIBRATION_SLOPE_DEFAULT = unset
NFL_TOTALS_CALIBRATION_SLOPE_MAX = unset
NFL_TOTALS_CALIBRATION_SLOPE_MIN = unset
NFL_TOTALS_EPA_INTERACTION_WEIGHT = unset
NFL_TOTALS_INJURY_STDEV_WEIGHT = unset
NFL_TOTALS_INJURY_WEIGHT = unset
NFL_TOTALS_LEVEL_SHIFT_SHRINK = unset
NFL_TOTALS_LEVEL_SHIFT_SHRINK_DEFAULT_WITH_PRIOR_DELTA = unset
NFL_TOTALS_MAX_ADJUSTMENT_POINTS = unset
NFL_TOTALS_MAX_STDEV_ADJUSTMENT = unset
NFL_TOTALS_PASS_RATE_WEIGHT = unset
NFL_TOTALS_SUCCESS_DELTA_WEIGHT = unset
```

No NaN / inf / empty string. Non-finite at remat/export/build remains **STOP** (C-9).

---

## 3. Q7 completeness memo (≤2023 REG only)

Verbatim rule (locked):

> The fit-window choice must rest on listing data-quality only, never on outcomes or performance. Pre-register now: a season is included only if >=95% of team-week listings have a non-NULL report_time < kickoff and >=90% of listed players resolve to a roster/depth id. Seasons failing either are dropped. Measure and file this before any fit. The window must end at 2023 either way.

**Measured 2026-10-23. No fit. No 2024/2025 injury, roster, or feature files opened. Schedule file was filtered to `season ∈ [2013, 2023]` and `game_type=REG` immediately; only `season, week, gameday, gametime, home_team, away_team` were read. Scores, results, totals, and closing lines were not used.**

| Item | Value |
|------|--------|
| A(S) | share of REG team-week listings with non-NULL `max(date_modified)` **< kickoff** |
| B(S) | share of listed player-rows whose `gsis_id` is on that season’s roster (team match, else season match) |
| `report_time` reconstruction | nflverse `date_modified` (warehouse `report_time` did not exist on ≤2023 dump) |
| Kickoff | `gameday` + `gametime` (ET wall clock; date-only → 23:59:59). Missing kickoff **fails** the team-week (not 0.0) |
| Listing source | nflverse `injuries_{2013..2023}.csv` |
| Roster source | nflverse `roster_{2013..2023}.csv` |
| Schedule source | nflverse `schedules/games.csv` kickoff columns only, ≤2023 REG |

### Season table

| Season | A(S) | A num/den | A fail (ts / ko / not-before) | B(S) | B num/den | Include |
|--------|------|-----------|-------------------------------|------|-----------|---------|
| 2013 | 1.000000 | 511/511 | 0 / 0 / 0 | 0.999796 | 4912/4913 | **yes** |
| 2014 | 1.000000 | 512/512 | 0 / 0 / 0 | 0.999796 | 4911/4912 | **yes** |
| 2015 | 0.998047 | 511/512 | 0 / 0 / 1 | 0.999601 | 5007/5009 | **yes** |
| 2016 | 1.000000 | 512/512 | 0 / 0 / 0 | 1.000000 | 4928/4928 | **yes** |
| 2017 | 1.000000 | 511/511 | 0 / 0 / 0 | 1.000000 | 4949/4949 | **yes** |
| 2018 | 0.996094 | 510/512 | 0 / 0 / 2 | 1.000000 | 4961/4961 | **yes** |
| 2019 | 0.998047 | 511/512 | 0 / 0 / 1 | 1.000000 | 5202/5202 | **yes** |
| 2020 | 0.998043 | 510/511 | 0 / 0 / 1 | 1.000000 | 5414/5414 | **yes** |
| 2021 | 0.998162 | 543/544 | 0 / 0 / 1 | 1.000000 | 5348/5348 | **yes** |
| 2022 | 0.996303 | 539/541 | 0 / 2 / 0 | 1.000000 | 5450/5450 | **yes** |
| 2023 | 1.000000 | 543/543 | 0 / 0 / 0 | 1.000000 | 5451/5451 | **yes** |

**Included seasons:** `{2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023}`.  
**Window:** 2013–2023 REG. **Ends at 2023 either way.**  
No season was added or dropped because of CLV, MAE, or any outcome.

Inner folds (design §6.2), still not run:

| Fold | Fit | Inner validate |
|------|-----|----------------|
| F1 | REG ≤ 2021 (all pass Q7) | 2022 REG |
| F2 | REG ≤ 2022 (all pass Q7) | 2023 REG |

---

## 4. Frozen grids (unchanged from design v2 §6.0)

| Object | Frozen candidates |
|--------|-------------------|
| θ | `{0.40, 0.60, 0.80}` |
| Cap \|Δspread\| | `{2.0, 2.6, 3.2}` |
| Cap \|Δtotal\| | `{2.0, 2.8, 3.4}` |
| Interior availability | doubtful `{0.15, 0.25, 0.35}`; questionable `{0.40, 0.50, 0.60}`; limited `{0.75, 0.85, 0.95}` |
| Out / IR / PUP / susp / inactive | **0.00 fixed** (not on the grid) |
| Specs | A / B / C as in design v2 §6.4 |
| Spec / grid selection | inner rolling-origin on included ≤2023 only. Never 2024/2025 |
| Primary endpoint | Q6 verbatim: mean spread CLV vs the **closing** line |
| Holdout gates | frozen v1 I-1..I-5 and K-2..K-4; not opened |

---

## 5. D-2 QB1-floor and healthy epsilon (a priori)

Set **now**, from structural priors / the existing identity threshold. **Not** from inner-fold outcome performance. If a later agent tunes these after seeing fold CLV, those supplements are NOT RUN (D-2).

| Name | Value | A-priori basis (no outcomes) |
|------|-------|------------------------------|
| **QB1-floor** (points of \|Δspread\|) | **1.5** | `injury_paths.player_offense_value` QB1 = **0.12** index units × structural 12.5 pts / index-unit on the full-strength prior = 1.5. Interior to the cap-grid minimum 2.0. **Not** taken from KEI `qb1_out_spread=3.5` (desk overlay; C-12 / D-2 forbid market-derived input). |
| **Healthy epsilon** | **0.05** | Existing `model_already_has_injury` identity (`margin` or `total` points > 0.05). Data-quality / identity threshold, not a fit. |

Cap **numbers** used in supplements remain the frozen cap grids above. No cap was chosen from a fold.

---

## 6. What is still forbidden

- Do **not** run the fit until IMV writes an acknowledgement of **this file’s sha256**.
- Do **not** build 2024 or 2025 feature or shadow rows (D-3: only after coefficient / fit-object shas freeze).
- Do **not** join outcomes or closing lines in any builder.
- Do **not** unlock overlays or apply on publish.
- Do **not** open the 2024/2025 holdout.

NO-GO. Coming Soon ON. ELIGIBLE ≠ CLEAR.

---

*D-4 amendment. Fit waits for IMV written acknowledgement of this sha.*
