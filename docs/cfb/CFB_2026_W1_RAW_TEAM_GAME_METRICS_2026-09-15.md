# CFB 2026 W−1 raw unadjusted team-game metrics

**Date:** 2026-09-15  
**Authorized:** Ryan / CoS GO — first KE-path _build_.  
**Product label:** raw unadjusted team-game metrics. **Not KE Ratings.**

Follows [#555](https://github.com/kosedge/kosedge/pull/555) `owned_metrics` definitions and [#558](https://github.com/kosedge/kosedge/pull/558) completed-game eligibility. Research-only.

Evidence: `data/ops/cfb-2026-w1-raw-team-game-20260915/`  
Bulk artifacts (gitignored): `data/cfb/research/pbp_current/as_of_20260915/`

---

## Scope

| In                                                       | Out                                                  |
| -------------------------------------------------------- | ---------------------------------------------------- |
| Versioned SDV 2026 PBP + refreshed schedule              | CFBD / PPA                                           |
| Actually completed ∩ PBP ∩ `week < W`                    | Live / HALFTIME / END_PERIOD / DELAYED-without-score |
| Unadjusted team-game metrics (`opponent_adjusted=false`) | Opponent-adjustment solver                           |
| Eligibility manifest + validation                        | Havoc / ST productization                            |
|                                                          | SP+ compose / KEI / Edge Board / NFL                 |

Success rate is labeled **`EPA_success = EPA>0`**. Standard 50/70/100 SR is a separate column.

---

## Paths

| Role                             | Path                                                       |
| -------------------------------- | ---------------------------------------------------------- |
| Historical CANONICAL (2014–2025) | `/Volumes/KosEdgeData/raw/cfb/pbp/` — **not written**      |
| Current-season HD target         | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/` |
| VM restore (gitignored)          | `data/cfb/research/pbp_current/as_of_20260915/`            |
| Committed evidence               | `data/ops/cfb-2026-w1-raw-team-game-20260915/`             |

This VM does not mount the Mac. HD target is documented only.

---

## Pipeline

Code: `cfb_warehouse.team_game_w1_2026` · version `cfb-2026-w1-raw-team-game-v1`  
Runner: `scripts/cfb/run_2026_w1_team_game_metrics.py`

1. Restore SDV `play_by_play_2026.parquet` + `cfb_schedule_2026.parquet` into the as_of folder.
2. Classify completion (#558): STATUS_FINAL **or** (scores present and not live).
3. Eligible = actually completed ∩ PBP ∩ `week < as_of_week`.
4. Compute #555 raw metrics on those plays only.
5. Write team-game table (off + def + opportunity / finish / field position) and eligibility manifest.
6. Validate: 0 unfinished rows; included games = manifest eligible; max week < W; SHA recorded; `opponent_adjusted=false`.

Default `as_of_week` = max completed∩PBP week + 1. This snapshot: **W = 3**.

---

## Live restore (as_of 20260915)

Input SHA matches the #558 proof snapshot.

| Input                       | SHA-256                                                            |     Bytes |
| --------------------------- | ------------------------------------------------------------------ | --------: |
| `play_by_play_2026.parquet` | `da0ec956d441da96aa0e85232fb685cb8408000fcf28a5fe5de0f3bb1d25e0ad` | 7,904,267 |
| `cfb_schedule_2026.parquet` | `bbc26106ca135be8a4da0202452b0fd4bbfe49081b7e1eb276cfb184409db768` |    16,867 |

| Eligibility                            |                  Count |
| -------------------------------------- | ---------------------: |
| Included (completed ∩ PBP ∩ week < 3)  |                 **85** |
| Excluded unfinished live (has PBP)     |                 **94** |
| Excluded unfinished live (no PBP)      |                      1 |
| Excluded parked / delayed 0–0 (no PBP) |                      5 |
| Completed missing PBP                  |                  **0** |
| Unmatched PBP                          |                  **0** |
| Table rows (team-games)                |                **170** |
| Table games                            |                 **85** |
| Unfinished rows in metrics table       |                  **0** |
| Weeks in table                         |                   1, 2 |
| max(week)                              | **2** (< as_of_week 3) |
| W−1 form teams                         |                    133 |

---

## Validation (all PASS)

| Check                                       | Result                                        |
| ------------------------------------------- | --------------------------------------------- |
| 0 unfinished rows in the metrics table      | PASS                                          |
| included count = manifest eligible count    | PASS (85 = 85)                                |
| leakage: only `week < W`                    | PASS (max week 2 < 3; kickoff week contract)  |
| core-31 present                             | **31 / 31**; absent = []                      |
| EPA null rate on scrimmage used             | **0** (0 / 10,748)                            |
| Other core-31 nulls                         | `start.yardsToEndzone` 0.014%; all others 0   |
| Input SHA recorded                          | PASS (table above)                            |
| `opponent_adjusted=false` on all rows       | PASS                                          |
| No write to Aug 13 `raw/cfb/pbp/` 2014–2025 | PASS (HD unmounted; repo hist lake untouched) |
| No SP+ compose / KEI / Edge Board           | PASS                                          |
| CFBD unused                                 | PASS                                          |
| Product label is not “KE Ratings”           | PASS                                          |

Eligible plays used: **14,331** (10,748 scrimmage). PPA not present; not invented.

---

## League rollup (unadjusted, 170 team-games)

| Metric                               |                 Value |
| ------------------------------------ | --------------------: |
| Success rate (`EPA_success = EPA>0`) |                 0.440 |
| Standard success rate (50/70/100)    |                 0.418 |
| EPA / play                           |                 0.035 |
| Explosive rate                       |                 0.206 |
| Pass / rush explosive                |         0.269 / 0.152 |
| Early / standard / passing-down SR   | 0.444 / 0.453 / 0.419 |

These are **raw team-game metrics**. They are not opponent-adjusted and are not KE Ratings.

---

## Unit tests

`pytest services/model-service/tests/test_cfb_2026_w1_team_game_metrics.py` — **11 passed**.

Covers live/HALFTIME/END_PERIOD/DELAYED-0–0 exclusion, `week < W` leakage, `EPA_success = EPA>0`, off/def/opportunity compose, historical-lake write refusal, and `opponent_adjusted=false`.

---

## STOP

- No opponent-adjusted KE Ratings.
- No havoc/ST productization (flags may exist on raw 2026; not wired).
- No PPA / CFBD.
- No NFL work.
- No live CFB compose / KEI / Edge Board change.
- No write to Aug 13 `raw/cfb/pbp/` 2014–2025.

**STOP.**
