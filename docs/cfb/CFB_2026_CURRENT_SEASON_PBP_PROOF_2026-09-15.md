# CFB 2026 current-season PBP proof (SportsDataverse / ESPN — no CFBD key)

**Date:** 2026-09-15 (coverage honesty amendment same day)  
**Lock:** Ryan / CoS — soft-park CFBD. Independent SportsDataverse `espn_cfb_pbp` + ESPN route only.  
**Follows:** [PR #555](https://github.com/kosedge/kosedge/pull/555) owned raw metrics; amends [PR #556](https://github.com/kosedge/kosedge/pull/556).  
**Scope:** Research retrieve + schedule reconcile + field-support matrix. No model fit. No opponent-adjusted ratings. No Edge Board / KEI / fair line.

Evidence: `data/ops/cfb-2026-current-season-proof-20260915/`

---

## 1. Retrieval (no CFBD)

| Asset | URL | HTTP | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| Season PBP parquet | `…/espn_cfb_pbp/play_by_play_2026.parquet` | 200 | 7,904,267 | `da0ec956d441da96aa0e85232fb685cb8408000fcf28a5fe5de0f3bb1d25e0ad` |
| Season schedule parquet (refreshed in-cloud) | `…/espn_cfb_schedules/cfb_schedule_2026.parquet` | 200 | 16,867 | `bbc26106ca135be8a4da0202452b0fd4bbfe49081b7e1eb276cfb184409db768` |
| Schedule `.csv.gz` (historical ingest name) | `…/cfb_schedule_2026.csv.gz` | **404** | — | use `.parquet` or `.csv` |
| ESPN core plays (sample `401864494` USC–SJSU) | `sports.core.api.espn.com/…/plays` | 200 | — | 165 plays reported |
| ESPN site summary (same game) | `site.api.espn.com/…/summary` | **403** from this VM | — | not required; season parquet is SoT |

Forced schedule re-download on 2026-09-15: **SHA and bytes unchanged** vs the first cloud pull. CoS Mac copy at `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_20260915/cfb_schedule_2026.parquet` may differ if that machine saw a later SDV publish; this VM reports the GitHub release as of the refresh.

`cfbd_*` was not called. `collegefootballdata.com` is denylisted in the proof module.

**In file:** 20,118 plays · 179 `game_id`s · season **2026 only** · weeks **1–2** · 498 columns · 0 duplicate `id`. This is an in-season slice (~7.9 MB), not a full-year lake.

---

## 2. HD versioning (do not overwrite 2014–2025)

| Role | Path |
| --- | --- |
| Historical CANONICAL (2014–2025) | `/Volumes/KosEdgeData/raw/cfb/pbp/play_by_play_{year}.parquet` |
| Current-season HD target | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_20260915/` |
| CoS inventory note (Mac) | `inventory/cfb/sdv-2026-schedule-reconcile-refresh-20260915.json` |
| This VM (gitignored restore) | `data/cfb/research/pbp_current/as_of_20260915/` |

`ingest_pbp` seasons remain **2014–2025**. Aug 13 inventory JSONs were **not** rewritten.

---

## 3. Schedule vs PBP — coverage honesty

**84/84 is `STATUS_FINAL` in that schedule snapshot ∩ PBP. It is not proof that every actually completed game is in PBP.** The schedule feed lags: many games that already have PBP still show `STATUS_IN_PROGRESS`.

Two completion views are reported separately:

| View | Definition | W−1? |
| --- | --- | --- |
| `status_final` | `STATUS_FINAL` / `COMPLETED` on **this** snapshot | No — snapshot-only |
| `actually_completed` | `STATUS_FINAL` **or** completed flag **or** (both scores present **and** status is not live), excluding parked 0–0 | Yes, if also in PBP |
| Unfinished | `IN_PROGRESS` / `HALFTIME` / `END_PERIOD`, parked 0–0, unmatched | **Excluded** from W−1 |

### All 179 PBP games (refreshed schedule)

| Bucket | Count | Meaning |
| --- | ---: | --- |
| Completed (`actually_completed` ∩ PBP) | **85** | 84 `STATUS_FINAL` + 1 `STATUS_DELAYED` 21–0 (Jacksonville State–Eastern Kentucky, `401868140`) |
| In progress (live status on snapshot) | **94** | Still `IN_PROGRESS` / `HALFTIME` / `END_PERIOD`. 19 of these already have ≥100 PBP plays — feed is stale, **still not treated as completed** |
| Postponed / delayed in PBP (not completed) | **0** | The one DELAYED-with-score is in the completed bucket |
| Unmatched (PBP `game_id` absent from schedule) | **0** | |
| **PBP total** | **179** | 85 + 94 |

### Schedule-side (185 games, weeks 1–2)

| | W1 | W2 | Total |
| --- | ---: | ---: | ---: |
| Scheduled | 99 | 86 | **185** |
| `STATUS_FINAL` | 53 | 31 | **84** |
| `STATUS_FINAL` ∩ PBP | 53 | 31 | **84 / 84 snapshot-final only** |
| `STATUS_FINAL` missing PBP | 0 | 0 | **0** |
| Actually completed | 54 | 31 | **85** |
| Actually completed ∩ PBP | 54 | 31 | **85** |
| Actually completed missing PBP | 0 | 0 | **0** |
| Schedule games with zero PBP | | | **6** (5 DELAYED 0–0 + UAB–ULM `IN_PROGRESS` 0–7) |

W−1 eligibility in this snapshot: **85 completed ∩ PBP**. **94 unfinished PBP games excluded.** Do not claim full completed-game coverage while 94 PBP games remain live-status on the feed.

---

## 4. Field support for #555 owned raw metrics

All **31** warehouse core columns are present. Null rates are ~0 except `start.yardsToEndzone` (0.0149%) and `EP_start` / `EP_end` (0.005%).

| #555 input / metric | Data | Notes |
| --- | --- | --- |
| `EPA` | **available** | null 0 |
| `EPA_success` | **available** | null 0 |
| `scrimmage_play` / `pass` / `rush` | **available** | |
| `down` / `distance` | **available** | |
| `start.yardsToEndzone` | **available** | 3 nulls / 20,118 |
| `drive.id` / `type.text` | **available** | |
| Pace / explosiveness / scoring-opp inputs | **available** | same #555 definitions |

**Havoc / ST field completeness (check before calling external):**

| Family | Present in 2026 raw | Next step |
| --- | --- | --- |
| Havoc flags | `havoc`, `TFL`, `sack`, `int`, `pass_breakup`, `forced_fumble` | **Validate** vs published havoc — do not declare NEED_EXTERNAL yet |
| Special teams | `type.text` Kickoff/Punt/FG + ~83 kick/punt/FG/return columns | **Validate** completeness / definition — do not declare NEED_EXTERNAL yet |
| PPA | **absent** | Optional only. Build around EPA. CFBD parked. |

---

## 5. ESPN individual-game path

Prefer the season parquet. Core plays API **200** for `401864494` (165 plays vs 160 in parquet). Site summary **403** from this VM.

---

## 6. STOP

- No CFBD key. No vendor shopping.
- No model / fair / Edge Board / KEI.
- No opponent-adjusted ratings in this PR.
- Historical 2021–2025 inventory files were not replaced.
- First bounded *implementation* task is recommended in the #556 amendment — **not built here**.

**STOP.**
