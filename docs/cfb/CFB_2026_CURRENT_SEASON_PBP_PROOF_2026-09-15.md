# CFB 2026 current-season PBP proof (SportsDataverse / ESPN — no CFBD key)

**Date:** 2026-09-15  
**Lock:** Ryan / CoS — soft-park CFBD. Independent SportsDataverse `espn_cfb_pbp` + ESPN route only.  
**Follows:** [PR #555](https://github.com/kosedge/kosedge/pull/555) owned raw metrics; amends [PR #556](https://github.com/kosedge/kosedge/pull/556) gap notes.  
**Scope:** Research retrieve + schedule reconcile + field-support matrix. No model fit. No opponent-adjusted ratings. No Edge Board / KEI / fair line.

Evidence: `data/ops/cfb-2026-current-season-proof-20260915/`

---

## 1. Retrieval (no CFBD)

| Asset | URL | HTTP | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| Season PBP parquet | `…/espn_cfb_pbp/play_by_play_2026.parquet` | 200 | 7,904,267 | `da0ec956d441da96aa0e85232fb685cb8408000fcf28a5fe5de0f3bb1d25e0ad` |
| Season schedule parquet | `…/espn_cfb_schedules/cfb_schedule_2026.parquet` | 200 | 16,867 | `bbc26106ca135be8a4da0202452b0fd4bbfe49081b7e1eb276cfb184409db768` |
| Schedule `.csv.gz` (historical ingest name) | `…/cfb_schedule_2026.csv.gz` | **404** | — | use `.parquet` or `.csv` |
| ESPN core plays (sample `401864494` USC–SJSU) | `sports.core.api.espn.com/…/plays` | 200 | — | 165 plays reported |
| ESPN site summary (same game) | `site.api.espn.com/…/summary` | **403** from this VM | — | not required; season parquet is SoT |

`cfbd_*` was not called. `collegefootballdata.com` is denylisted in the proof module.

**In file:** 20,118 plays · 179 `game_id`s · season **2026 only** · weeks **1–2** · 498 columns · 0 duplicate `id`. This is an in-season slice (~7.9 MB), not a full-year lake.

---

## 2. HD versioning (do not overwrite 2014–2025)

The Aug 13 historical lake stays canonical. 2026 is versioned on a **different** tree:

| Role | Path |
| --- | --- |
| Historical CANONICAL (2014–2025) | `/Volumes/KosEdgeData/raw/cfb/pbp/play_by_play_{year}.parquet` |
| Current-season HD target (CoS / Mac) | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/` |
| This proof’s HD target | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_20260915/` |
| This VM (gitignored restore) | `data/cfb/research/pbp_current/as_of_20260915/` |

`ingest_pbp` seasons remain **2014–2025**. Committed Aug 13 inventory JSONs were **not** rewritten. Writes into `raw/cfb/pbp/` are refused by the proof loader.

This VM cannot mount the Mac disk (`hd_mounted=false`). Copy the research parquet onto the HD target when the drive is attached.

---

## 3. Schedule vs PBP coverage

SDV schedule snapshot: **185** games (weeks 1–2, `game_date` 2026-08-29 → 2026-09-13).

| | Week 1 | Week 2 | Total |
| --- | ---: | ---: | ---: |
| Scheduled | 99 | 86 | **185** |
| `STATUS_FINAL` | 53 | 31 | **84** |
| FINAL present in PBP | 53 | 31 | **84 (100%)** |
| FINAL missing PBP | 0 | 0 | **0** |

| Gap | Count | Honesty |
| --- | ---: | --- |
| PBP games | 179 | Includes non-FINAL status on the schedule snapshot |
| Schedule not FINAL (IN_PROGRESS / DELAYED / HALFTIME / END_PERIOD) | 101 | Schedule status is **stale** on a Tuesday as_of — many weekend games still say IN_PROGRESS |
| Those non-FINAL games that already have PBP | 95 | Do **not** treat as W−1 completed form until independently finalized |
| Schedule games with **zero** PBP | 6 | 5× `STATUS_DELAYED` 0–0 (Duke–Tulane, Charlotte–Citadel, Pitt–UCF, Auburn–USM, Clemson–Ga Southern) + UAB–ULM `IN_PROGRESS` 0–7 |

**Completed-game coverage is complete. Live/stale-status coverage is not.** For 2026 W−1 features, restrict to `STATUS_FINAL` (or an equivalent completed gate) and `week < W`.

---

## 4. Field support for #555 owned raw metrics

All **31** warehouse core columns are present. Null rates are ~0 except `start.yardsToEndzone` (0.0149%) and `EP_start` / `EP_end` (0.005%).

| #555 input / metric | Class | Notes |
| --- | --- | --- |
| `EPA` | **SUPPORTED** | null 0 |
| `EPA_success` | **SUPPORTED** | null 0 |
| `scrimmage_play` | **SUPPORTED** | ~75.3% of rows truthy |
| `pass` / `rush` | **SUPPORTED** | |
| `down` / `distance` | **SUPPORTED** | early / standard / passing-down splits |
| `start.yardsToEndzone` | **SUPPORTED** | 3 nulls / 20,118 |
| `drive.id` | **SUPPORTED** | |
| `type.text` | **SUPPORTED** | scoring / parse |
| Pace (plays / team-game) | **SUPPORTED** | `scrimmage_play` + `game_id` + `pos_team` |
| True pace (competitive) | **SUPPORTED** | + `pos_score_diff` |
| Explosiveness | **SUPPORTED** | `EPA` + `statYardage` + pass/rush |
| Scoring opportunity / finishing inputs | **SUPPORTED** | drive + yards-to-endzone + `type.text`; `scoring_opp` / `rz_play` also present |

**Not supported / not verified**

| Item | Class | Notes |
| --- | --- | --- |
| PPA | **ABSENT** | no `PPA`/`ppa` column — optional; CFBD parked |
| Havoc boolean | **PRESENT, UNVERIFIED** | `havoc` / `TFL` / `sack` / `int` exist (havoc ~11.9% of all plays). Field-verify vs published havoc later. |
| Special teams | **UNVERIFIED** | not a #555 raw-metric SoT |
| Opponent-adjusted EPA / KE ratings | **OUT OF SCOPE** | separate work |

This proof does **not** rematerialize team-game metrics. It shows the 2026 parquet can feed the same unadjusted definitions as #555.

---

## 5. ESPN individual-game path

Prefer the season parquet. For one FINAL game (`401864494`):

- Core plays API: **200**, 165 plays (parquet had 160 for that `game_id` — small ST/pagination difference, not a second vendor).
- Site summary API: **403** from this datacenter. Do not treat that as a CFBD problem.

---

## 6. STOP

- No CFBD key. No vendor shopping.
- No model / fair / Edge Board / KEI.
- No opponent-adjusted ratings.
- Historical 2021–2025 inventory files were not replaced.
- Remaining work is listed in the #556 amendment — not authorized here.

**STOP.**
