# CFB 2026 W−1 raw unadjusted team-game metrics

**Date:** 2026-09-15  
**Authorized:** Ryan / CoS GO — first KE-path *build*.  
**Product label:** raw unadjusted team-game metrics. **Not KE Ratings.**

Follows [#555](https://github.com/kosedge/kosedge/pull/555) `owned_metrics` definitions and [#558](https://github.com/kosedge/kosedge/pull/558) completed-game eligibility. Research-only.

---

## Scope

| In | Out |
| --- | --- |
| Versioned SDV 2026 PBP + refreshed schedule | CFBD / PPA |
| Actually completed ∩ PBP ∩ `week < W` | Live / HALFTIME / END_PERIOD / DELAYED-without-score |
| Unadjusted team-game metrics (`opponent_adjusted=false`) | Opponent-adjustment solver |
| Eligibility manifest + validation | Havoc / ST productization |
| | SP+ compose / KEI / Edge Board / NFL |

Success rate is labeled **`EPA_success = EPA>0`**. Standard 50/70/100 SR is a separate column.

---

## Paths

| Role | Path |
| --- | --- |
| Historical CANONICAL (2014–2025) | `/Volumes/KosEdgeData/raw/cfb/pbp/` — **do not write** |
| Current-season HD target | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/` |
| VM restore (gitignored) | `data/cfb/research/pbp_current/as_of_YYYYMMDD/` |
| Committed evidence | `data/ops/cfb-2026-w1-raw-team-game-20260915/` |

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

Default `as_of_week` = max completed intersect PBP week + 1 (current snapshot includes all completed games and none of the live-status PBP games).

---

## Unit tests

`pytest services/model-service/tests/test_cfb_2026_w1_team_game_metrics.py` — **11 passed**.

Covers live/HALFTIME/END_PERIOD/DELAYED-0–0 exclusion, `week < W` leakage, `EPA_success = EPA>0`, off/def/opportunity compose, historical-lake write refusal, and `opponent_adjusted=false`.

---

## Live SDV restore (this revision)

Pending the research runner against the 2026-09-15 snapshot. Expected from #558: **~85** eligible completed∩PBP, **~94** live-status PBP excluded, 0 unmatched, 0 completed-missing-PBP.

Fill-in after `python scripts/cfb/run_2026_w1_team_game_metrics.py --as-of 20260915 --commit-ops`:

| Check | Result |
| --- | --- |
| Eligible games | *pending live restore* |
| Table rows / games | *pending* |
| Unfinished rows | must be 0 |
| Included = manifest eligible | must match |
| max(week) < as_of_week | must hold |
| core-31 / EPA null (scrimmage) | report |
| PBP SHA / schedule SHA | record |
| `opponent_adjusted=false` | all rows |
| Historical lake write | false |
| CFBD / SP+ / KEI | unused / unchanged |

---

## STOP

- No opponent-adjusted KE Ratings.
- No havoc/ST productization.
- No PPA / CFBD.
- No NFL work.
- No live CFB compose / KEI / Edge Board change.
- No write to Aug 13 `raw/cfb/pbp/` 2014–2025.

**STOP.**
