# CFB owned PBP loader, raw metrics, and validation

**Date:** 2026-09-15  
**Follows:** [PR #555](https://github.com/kosedge/kosedge/pull/555) inventory (`docs/cfb/CFB_OWNED_DATA_INVENTORY_GAP_2026-09-15.md`)  
**Authorized:** Ryan / CoS — next step after inventory. No vendor shopping.  
**Scope:** Research-only loader + raw metrics + evidence. No model fit, no fair line, no Edge Board, no KEI, **no opponent-adjusted EPA / KE ratings**.

Evidence: `data/ops/cfb-owned-pbp-research-20260915/evidence.json`  
Checksums: `data/ops/cfb-owned-pbp-research-20260915/checksums.json`

---

## 1. What ran

This cloud agent **cannot see Ryan’s Mac**. `/Volumes/KosEdgeData` is unmounted here (same as the inventory checkout).

To produce validation evidence without a new vendor, the research runner restored the **same SportsDataverse `espn_cfb_pbp` release** already documented as owned (`--allow-fetch`). That is a restore copy, not the Aug 13 HD bytes.

| Location                                                      | Status                                                           |
| ------------------------------------------------------------- | ---------------------------------------------------------------- |
| `/Volumes/KosEdgeData/raw/cfb/pbp/`                           | Not visible in this environment                                  |
| Repo fallback `data/cfb/warehouse/` (gitignored)              | Intended path after loader fix                                   |
| Accidental write `services/model-service/data/cfb/warehouse/` | Where this run landed (path resolver bug; now fixed; gitignored) |
| Railway                                                       | Still no CFB parquet volume                                      |

**67% DIRECT+DERIVABLE in #555 is coverage of nine feature requirements, not model completeness.** This PR implements the raw owned metrics. It does **not** make a production rating.

---

## 2. 2025 parquet validation (unlocked this PR only)

Documented HD paths were not readable here. Validation is of the **current SDV `play_by_play_2025.parquet` restore** plus a generated 31-column core.

| Check                        | Result                                                             |
| ---------------------------- | ------------------------------------------------------------------ |
| Seasons in file              | **2025 only**                                                      |
| Plays                        | **166,053** (inventory 165,850; **+203**)                          |
| Unique games                 | **956** (inventory **match**)                                      |
| Unique `pos_team`            | **236** (FBS + FCS names)                                          |
| Raw columns                  | **496** (inventory 476; **+20**)                                   |
| Core columns                 | **31 / 31** present                                                |
| Duplicate `id`               | **0**                                                              |
| Raw vs core play/game delta  | **0**                                                              |
| `start.yardsToEndzone` nulls | **0.0036%**                                                        |
| All other core-31 nulls      | **0**                                                              |
| Raw sha256                   | `aa037920e980acf17317747f2010a031b3b7e1013a44a7b15db18b1dd9df0e63` |
| Core sha256                  | `56d953583e6803a31bff878335774e2015a7ca12066eb07dcea195c5f2e41684` |

2025 was **not** used to fill 2021–2024 gaps. Completeness vs the Aug 13 inventory is **game-complete, play-count drifted** (later SDV publish of the same tag).

Raw 2025 also exposes `scoring_opp`, `sack`, `TFL`, `int`, `havoc` (boolean flags). Those are **not** in core-31 and were not used for the 2021–2024 metric rollups below.

---

## 3. 2021–2024 loader + inventory reconciliation

Loader: `cfb_warehouse.owned_pbp`

- Prefer HD raw/core
- Else gitignored repo fallback
- Optional `--allow-fetch` restore of the owned SDV URL
- SHA-256 of whatever bytes were actually read
- Reconcile plays / games / cols / bytes to the committed Aug 13 inventory

|        Season | Games vs inv | Plays restore |   Plays inv |    Δ plays |   Raw cols | Dup `id` |
| ------------: | ------------ | ------------: | ----------: | ---------: | ---------: | -------: |
|          2021 | 842 =        |       147,319 |     146,367 |       +952 | 497 vs 477 |        0 |
|          2022 | 861 =        |       149,700 |     149,654 |        +46 | 497 vs 477 |        0 |
|          2023 | 903 =        |       153,690 |     153,626 |        +64 | 497 vs 477 |        0 |
|          2024 | 946 =        |       163,142 |     162,950 |       +192 | 497 vs 477 |        0 |
| **2021–2024** | **3,552 =**  |   **613,851** | **612,597** | **+1,254** |            |    **0** |

**Games match the inventory exactly. Plays do not** — restore is a later copy of the same release tag, not a silent year drop. HD Aug 13 checksums remain unknown until someone hashes the Mac files.

2024 unique `pos_team`: **235**.

---

## 4. What `EPA_success` actually is

On **469,826** 2021–2024 scrimmage plays with finite EPA:

| Comparison                                             |    Agreement |
| ------------------------------------------------------ | -----------: |
| `EPA_success` ≡ `EPA > 0`                              | **1.000000** |
| `EPA_success` ≡ `EPA ≥ 0`                              |     0.999883 |
| `EPA_success` ≡ standard SR (50/70/100% of `distance`) | **0.939875** |

**Verdict: `EPA_success` is “positive EPA,” not Football Study Hall success rate.**  
Standard-SR on the same plays is 0.427 vs EPA-success 0.438. The research metric `success_rate` uses the vendor column and labels it as such. `standard_success_rate` is the 50/70/100 definition.

Zero cases of `EPA_success=true` with `EPA ≤ 0`.

---

## 5. Implemented raw metrics (research-only)

Code: `cfb_warehouse.owned_metrics` · version `cfb-owned-raw-metrics-v1`  
`opponent_adjusted = false` on every row.

Definitions and denominators are in `DEFINITIONS` (also copied into evidence.json). Short form:

| Metric                                   | Numerator                                        | Denominator                                                       |
| ---------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| Success rate                             | scrimmage plays with `EPA_success`               | scrimmage plays with non-null `EPA_success`                       |
| Standard SR                              | yards ≥ 50/70/100% of `distance`                 | scrimmage with finite down/distance/yards                         |
| EPA/play                                 | sum EPA                                          | scrimmage with finite EPA                                         |
| Pace                                     | scrimmage plays as `pos_team`                    | team-games                                                        |
| True pace (competitive)                  | those plays with \|score diff\| < 16             | team-games                                                        |
| Explosive                                | EPA ≥ 1.0 **or** yards ≥ 15                      | scrimmage with finite EPA or yards                                |
| Pass/rush explosive                      | same, filtered by `pass` / `rush`                | pass or rush scrimmage plays                                      |
| Early / standard / passing down SR & EPA | same success/EPA                                 | plays in that down bucket (early and standard **overlap** on 1st) |
| Scoring opportunity                      | drive reaches `yardsToEndzone` ≤ 40 or `rz_play` | drives (`game_id` + `drive.id`)                                   |
| Points / finish                          | `type.text` TD=6, XP=1, 2pt=2, FG=3, safety=2    | opportunity drives                                                |
| Field position                           | first-play `start.yardsToEndzone`                | drives                                                            |
| Drive EPA                                | sum of scrimmage EPA on the drive                | drives with ≥1 EPA                                                |
| Rolling form                             | team means of the above                          | games with `week < as_of_week` only                               |

**2021–2024 league (restore copy, unadjusted):**

| Metric                           |                                 Value |
| -------------------------------- | ------------------------------------: |
| Team-games                       |                                 7,104 |
| Plays / offense game             |                                 66.14 |
| Competitive plays / offense game |                                 49.80 |
| Success rate (`EPA>0`)           |                                 0.438 |
| Standard success rate            |                                 0.427 |
| EPA / play                       |                                 0.041 |
| Explosive rate                   |                                 0.215 |
| Pass / rush explosive            |                         0.272 / 0.159 |
| Early / standard / passing SR    |                 0.437 / 0.448 / 0.421 |
| Drives                           |                                89,719 |
| Opportunity rate                 |                                 0.456 |
| Points per opportunity           |                                  3.51 |
| Finish rate                      |                                 0.683 |
| Mean start yards-to-endzone      |                                  57.9 |
| Mean drive EPA sum               |                                 0.268 |
| 2024 form as_of week 8           | 230 teams; max `feature_week` = **7** |

These are **raw efficiency metrics. They do not establish opponent-adjusted EPA.**

---

## 6. CFBD authentication

| Check                                                              | Result                                                                  |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Env in this process (`CFBD_API_KEY` / `CFBD_KEY` / `BEARER_TOKEN`) | **Absent**                                                              |
| Unauthenticated `GET /conferences`                                 | **401**                                                                 |
| Repo / `.env`                                                      | No committed key (correct)                                              |
| Railway `model-service` production variables                       | **`CFBD_API_KEY` name is present** (value sealed; not read, not pasted) |

**Ryan account dependency:** a working API key (or a rotation if Railway’s stored key is still rejected) must be issued from **Ryan’s CollegeFootballData account** and written to Railway `CFBD_API_KEY`. This agent did not invent or copy a key.

Starter Pack ≠ API. Historical 2021–2024 work continued without CFBD.

---

## 7. 2026 W−1 ingest (scaffold)

`cfb_warehouse.season_2026_w1`

- Predictive features for week **W** use only `season=2026` and `week < W`.
- Kickoff `available_at` contract unchanged (`strictly_before_kickoff`).
- 2026 PBP is **missing on HD/fallback** in this run. Scaffold returns `no_2026_plays_before_cutoff` with `leakage_ok=true`.
- Same SDV URL `play_by_play_2026.parquet` **HEAD 200**, Content-Length **7,904,267** (in-season, smaller than a full year). **Not downloaded** in this PR.
- Alternate path when auth works: CFBD `/plays` + `/drives` for **completed** games only.
- Outputs stay research-only. No season-engine request-path wiring.

---

## 8. Railway data-availability plan (plan only)

Railway **cannot** read `/Volumes/KosEdgeData`. Do **not** invent a production SMB/AFP mount to the Mac.

Concrete options, in preferred order:

1. **Railway volume on `model-service-worker` (and API if a job runs there)**
   - Mount e.g. `/data/cfb/warehouse`.
   - Copy **core** 2021–2024 (~36 MB) plus 2025 core (~10 MB) from the Mac (or this restore) using `checksums.json` as the accept test.
   - Add raw 2021–2024 (~200 MB) only if sack/TFL/havoc flags are needed in production jobs.
   - Set `CFB_WAREHOUSE_ROOT=/data/cfb/warehouse` (loader change when that job is authorized).
   - Verify sha256 after copy. Fail closed if mismatch.

2. **Object store (R2/S3) + boot sync**
   - Upload the same parquet + checksum manifest.
   - Worker pulls to the volume or local disk on deploy.
   - Same checksum gate.

3. **Postgres load of core-31**
   - ~614k rows × 31 columns into a `cfb_wh_pbp` table (DDL in `051` is metadata only today).
   - Heavier ops; useful if volume policy is blocked.
   - Still not an opponent-adj mart.

**Not acceptable:** pointing production at Ryan’s laptop; silent empty-dir fallback that looks like “no CFB history.”

This PR does **not** create a Railway volume or upload bytes.

---

## 9. Remaining gaps

- HD Aug 13 **byte identity** still unverified (Mac not mounted here). Game counts match; play counts drifted on restore.
- **PPA** still absent from SDV raw (2022 and 2024 checked). CFBD `/ppa` still required if PPA is mandatory.
- **Havoc-as-published (PBU-inclusive)** — raw restore has a boolean `havoc` plus `sack` / `TFL` / `int` (2024: havoc 7.7%, TFL 6.5%, sack 2.2%). Not wired into v1 metrics (core-31 only). Confirm definition vs Bill C havoc before treating as SoT.
- **2026 current-season PBP** not loaded; W−1 scaffold only. CFBD auth still 401 in this process.
- **Opponent-adjusted EPA / KE ratings** — separate work. Not started.
- Production jobs still have **no lake**. Plan in §8 only.
- Points-per-opportunity uses `type.text` heuristics (TD without XP stays 6).

---

## 10. Code / tests

| Piece             | Path                                                                     |
| ----------------- | ------------------------------------------------------------------------ |
| Loader            | `services/model-service/src/services/cfb_warehouse/owned_pbp.py`         |
| Raw metrics       | `…/owned_metrics.py`                                                     |
| CFBD probe        | `…/cfbd_auth.py`                                                         |
| 2026 W−1 scaffold | `…/season_2026_w1.py`                                                    |
| Runner            | `scripts/cfb/run_owned_pbp_research.py`                                  |
| Tests             | `services/model-service/tests/test_cfb_owned_pbp_metrics.py` (11 passed) |
| Path fix          | `paths.py` now requires `apps/web` to identify the monorepo              |

Bulk parquet is gitignored. Do not commit it.

---

## 11. STOP

- No vendor shopping.
- No model / fair / Edge Board / KEI.
- No opponent-adjustment solver.
- No 2025→historical synthetic fill.
- No Railway mount invented.

**STOP.**
