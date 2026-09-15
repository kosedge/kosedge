# CFB owned-data inventory and Data Layer v2 gap

**Date:** 2026-09-15  
**Lock:** CoS / Ryan — pause external acquisition. CFBD API remains a live option (auth was the problem, not missing history). Starter Pack ≠ CFBD API. Do not purchase. Do not search replacement vendors.  
**Scope:** Inventory of CFB historical assets already owned in the repository and documented data-lake paths. No model fit. No scoring-equation change. No 2025 PBP/file access. No synthetic fills.  
**This checkout:** `/Volumes/KosEdgeData` is **not mounted**. Repo fallback `data/cfb/warehouse/{raw,clean}/` is **gitignored and empty**. Railway production has **no CFB parquet volume** (Postgres + Redis only). Bulk PBP is therefore **documented, not byte-verified here**.

**Follow-on (same PR / branch):** research loader + raw metrics + 2025 validation — `docs/cfb/CFB_OWNED_METRICS_VALIDATION_2026-09-15.md`. Not opponent-adjusted. Not a model.

---

## 1. Executive summary

The SportsDataverse / cfbfastR play-by-play claim is **true as a 2026-08-13 HD ingest**, not as an in-repo or Railway store.

| Claim | Verdict |
| --- | --- |
| SportsDataverse `espn_cfb_pbp` for **2021–2024** already ingested | **Yes, on paper.** Committed inventory lists 4 seasons, 612,597 plays, 3,552 PBP games, ~477 raw columns, 31-column core. Paths are `/Volumes/KosEdgeData/raw/cfb/pbp/play_by_play_{year}.parquet` and `clean/cfb/historical/pbp/pbp_{year}_core.parquet`. |
| Those files exist in git | **No.** Zero `.parquet` in the repo. |
| Those files exist in this environment | **No.** HD unmounted; warehouse fallback empty. |
| Those files exist on Railway | **No.** No data-lake volume. `cfb_wh_*` DDL exists; warehouse tables were **not loaded**. |
| HD still intact on the original ingest machine | **Unverified here.** A later job (2026-09-03 spread-tag holdout) recorded the lake **absent** and `data/cfb/warehouse` **empty** on that runner. |

**Honest feature split — 9 requested Data Layer v2 bullets (HD-conditional; weakest class when a bullet is mixed):**

| Class | Count | Share |
| --- | ---: | ---: |
| OWNED_DIRECT | 1 | **11%** (success rate only) |
| OWNED_DERIVABLE | 5 | **56%** |
| NEED_EXTERNAL | 3 | **33%** (EPA-or-PPA, havoc bundle, 2026 form) |
| UNSAFE_OR_UNKNOWN | 0 | **0%** of the 9 (missingness is a data-quality flag, not a feature) |

**Owned usable (DIRECT + DERIVABLE) = 67% of the 9 — not 100%.** That 67% is **conditional on HD still being present**. In *this* checkout the usable share of PBP-backed features is **0%** (inventories only).

Atomic split (12 rows in §5, treating EPA and PPA separately; field-position/drive as one DERIVABLE): DIRECT 2 (17%) · DERIVABLE 7 (58%) · EXTERNAL 3 (25%). Column missingness / unlisted raw-477 flags remain **UNSAFE_OR_UNKNOWN** and are excluded from the %.

Do not pad: current-season (2026) rolling form, CFBD **PPA**, and charted **havoc (PBU / official TFL)** are not owned. Success rate and EPA *columns* are owned in the documented core extract, but the requested “EPA or PPA” bullet is classified NEED_EXTERNAL because PPA is absent. Pace, explosiveness, down splits, field position, and drive aggregates are derivable from core — they are not pre-materialized marts.

**Smallest remaining external-data requirement is CFBD API (existing account), not a purchase and not a new vendor.** See §7.

---

## 2. SportsDataverse 2021–2024 PBP — what is actually present

### 2.1 Coverage (from committed inventory only; 2025 files not opened)

Source snapshot: `data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json` (`as_of` **2026-08-13**).

| Season | Status | Plays | PBP games | Raw cols | Core cols | Raw bytes |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | ok | 146,367 | 842 | 477 | 31 | 48,771,364 |
| 2022 | ok | 149,654 | 861 | 477 | 31 | 49,703,907 |
| 2023 | ok | 153,626 | 903 | 477 | 31 | 50,724,205 |
| 2024 | ok | 162,950 | 946 | 477 | 31 | 55,106,146 |
| **2021–2024** | | **612,597** | **3,552** | 477 | 31 | **~204 MB** |

Cross-check from the same ingest’s games spine (`cfb-historical-warehouse-v1-20260812-inventory.json`; STATUS_FINAL, 2020–…):

| Season | Warehouse games | Close spread | Open / lake primary | FCS-flagged |
| ---: | ---: | ---: | ---: | ---: |
| 2021 | 891 | 814 | 696 | 116 |
| 2022 | 900 | 838 | 717 | 119 |
| 2023 | 911 | 907 | 713 | 116 |
| 2024 | 965 | 965 | 793 | 166 |

PBP game counts are **lower** than warehouse finals (2021: 842 vs 891; 2022: 861 vs 900; 2023: 903 vs 911; 2024: 946 vs 965). Not a silent year drop — join is ESPN `game_id` — but coverage is **not 1:1**.

**Teams**

- Unique `pos_team` / `def_pos_team` counts were **never written** to the inventory.
- Identity spine: **136** packaged FBS engine codes; warehouse ingest recorded **136** teams / **293** aliases (this checkout’s `identity.py` now emits **307** alias rows — map drift after ingest).
- Efficiency build (`cfb-efficiency-preseason-prior-v1-20260812-inventory.json`) recorded FBS team-games: 2021 **1,575** / 2022 **1,596** / 2023 **1,679** / 2024 **1,684**. FCS plays were **flagged, not deleted**.
- Week-snapshot row counts (2,128 / 2,160 / 2,160 / 2,278) are consistent with ~133–135 FBS teams × ~16–17 as-of weeks. That is **inferred**, not a stored unique-team census.

### 2.2 Schema

**Core extract (31 columns, committed list).** This is the only column list Kos Edge recorded:

```
season, week, game_id, id, drive.id,
pos_team, def_pos_team,
homeTeamAbbrev, awayTeamAbbrev, homeTeamName, awayTeamName,
down, distance, start.yardsToEndzone, statYardage, type.text,
EPA, EP_start, EP_end, EPA_success,
rz_play, stuffed_run, pos_score_diff,
start.TimeSecsRem, under_2,
wpa, wp_before, wp_after,
scrimmage_play, pass, rush
```

`efficiency_adj.PBP_READ_COLS` also expects `half` and `period` when present in raw (used for garbage-time). Those two are **not** in the published core-31 list.

**Raw season files:** ~477 columns (`2020`/`2025` inventories say 476 — **2025 not inspected**). The extra ~446 names were **never committed**. This report does not invent them.

**Not in core-31 (material for Data Layer v2):** `sack`, TFL, PBU, forced fumble, interception/fumble flags, PPA, drive result / drive points, official scoring-opportunity flag, clock as game-seconds.

`type.text` is in core and is the ESPN play-type string (sack / interception / TD / FG language is typically here). That is a **text parse**, not a certified advanced-stat flag.

### 2.3 Missingness

**Not measured.** No null-rate table exists in the committed inventories. The efficiency builder **skips plays with missing/non-finite `EPA`**, which proves some EPA holes exist but not the rate.

Because the parquet is not on this disk, column-level missingness for 2021–2024 is **UNSAFE_OR_UNKNOWN** in this checkout.

### 2.4 Provenance

| Field | Recorded value |
| --- | --- |
| Source label | `sportsdataverse espn_cfb_pbp (load_cfb_pbp)` |
| Release tag | `espn_cfb_pbp` |
| Fetch URL pattern | `https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_cfb_pbp/play_by_play_{year}.parquet` |
| Ingest code | `scripts/cfb/ingest_historical_warehouse.py` → `cfb_warehouse.pbp.ingest_pbp` → `cfb_warehouse.sdv.fetch_sdv_file` |
| Ingest date | **2026-08-13** (`as_of` on both warehouse + PBP inventory JSONs) |
| SDV package version / release SHA | **Not recorded** |
| Doctrine | Download-once ingest. Not a live request path. Opponent-adj mart is a later pass; PBP files are the input. |

This is **SportsDataverse PBP**, not a CFBD Starter Pack dump.

---

## 3. Asset inventory

Presence codes: **GIT** = committed file; **HD-DOC** = documented on `/Volumes/KosEdgeData` as of 2026-08-13; **ABSENT-HERE** = not on this VM; **RAIL-NO** = not on Railway volumes.

| Asset | Path | Seasons (owned / documented) | Games | Teams | Rows | Provenance | Presence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SDV raw PBP | `/Volumes/KosEdgeData/raw/cfb/pbp/play_by_play_{y}.parquet` | **2014–2024 documented** (ingest range also listed 2025; **2025 not accessed**) | 2021–24: 3,552 | unique not stored; 136 FBS codes + FCS flags | 2021–24: 612,597 plays | SportsDataverse `espn_cfb_pbp` 2026-08-13 | HD-DOC / ABSENT-HERE / RAIL-NO |
| SDV PBP core | `/Volumes/KosEdgeData/clean/cfb/historical/pbp/pbp_{y}_core.parquet` | same | same | same | same plays × 31 cols | subset of raw | HD-DOC / ABSENT-HERE |
| PBP inventory JSON | `data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json` | lists 2014–… | 10,297 all listed seasons | n/a | counts only | ingest write-back | GIT |
| Games spine | `/Volumes/KosEdgeData/clean/cfb/historical/games.parquet` | 2020–… (2021–24: 3,667 finals) | 3,667 (2021–24) | 136 + FCS | 3,667 | SDV schedules + box + linescores | HD-DOC / ABSENT-HERE |
| Teams / aliases | `…/teams.parquet`, `team_aliases.parquet` | season=0 (2026 map) | n/a | 136 / 293 | 136 / 293 | packaged engine codes | HD-DOC / ABSENT-HERE |
| Closing lines | `…/closing_lines.parquet` | 2020–… | 5,196 all listed | — | 5,196 | Odds API lake primary + SDV betting fill | HD-DOC / ABSENT-HERE |
| SDV odds snapshots (fill) | `…/odds_snapshots.parquet` | 2020–… | 5,196 | — | 5,196 | `espn_cfb_betting` | HD-DOC / ABSENT-HERE |
| Odds API lake | `/Volumes/KosEdgeData/clean/odds/cfb/snapshots-{year}.parquet` | 2020–2026 documented | 4,736 lake games | — | 174,606 snaps | owned `odds_snapshots` Postgres export 2026-08-13 | HD-DOC / ABSENT-HERE |
| Warehouse inventory JSON | `data/ops/cfb-historical-warehouse-v1-20260812-inventory.json` | counts | 5,196 | 136 | counts | ingest write-back | GIT |
| Opponent-adj efficiency parquet | `/Volumes/KosEdgeData/clean/cfb/historical/efficiency/*.parquet` | 2014–… documented | team-games 20,588 | FBS + FCS | 20,588 team-games; 25,741 week rows | derived from owned PBP 2026-08-13 | HD-DOC / ABSENT-HERE |
| Efficiency inventory JSON | `data/ops/cfb-efficiency-preseason-prior-v1-20260812-inventory.json` | counts | — | — | counts | `efficiency_adj.build_efficiency` | GIT |
| Packaged 2026 preseason prior | `services/model-service/src/services/cfb_season_engine/data/cfb_preseason_prior_2026.json` | prior uses seasons **&lt; 2026** | n/a | 147 | 147 teams | warehouse prior; `as_of=2026-08-12` | GIT |
| SP+ 2025→2026 carry | `…/cfb_efficiency_snapshot_2025_carry_2026.json` | **prior-year ratings, not PBP** | n/a | 147 (141 mapped) | team rows | public SP+ table; `pbp: not_used` | GIT (metadata only; 2025 PBP not used) |
| 2026 roster snapshot | `…/cfb_real_roster_snapshot_2026.json` + `data/cfb/raw/package_real_roster_summary.json` | 2026 identity | n/a | 145 rosters | 14,453 athletes | ESPN public roster; CFBD overlay **skipped** | GIT |
| 2026 slate / universe / KEI / futures | `cfb_*_2026.json` under season-engine + `apps/web/lib/data/` | 2026 product | slate games | FBS | packaged | official slate / engine artifacts | GIT |
| 2026 Odds API events stub | `data/cfb/raw/odds_api_ncaaf_events_2026.json` | 2026 | events file | — | file | Odds API | GIT |
| Hist-cal reports | `data/ops/cfb-historical-calibration-20260805*` | 2022–… holdout metrics | samples | — | metrics | SDV betting/box/linescores + `cfb_ratings` (fetched at run; **not committed as lake**) | GIT (metrics) |
| Postgres `cfb_wh_*` | `infra/db/051_cfb_historical_warehouse.sql` | DDL only | — | — | **empty unless loaded** | metadata contract | GIT DDL / RAIL-NO load |
| Repo warehouse fallback | `data/cfb/warehouse/{raw,clean}/` | — | 0 | 0 | 0 | gitignored | ABSENT-HERE |
| CFBD Starter Pack | — | — | — | — | — | **not present** | none |
| CFBD API extracts | — | — | — | — | — | optional overlay coded; last roster pack `cfbd.enabled=false` | none owned |

**Not CFB PBP (excluded from ownership claim):** `apps/web/data/raw/ratings/*` (CBB KenPom/Barttorvik/Haslametrics), NFL PBP SQL, 2026 UI JSON copies.

---

## 4. Can owned PBP derive the Data Layer v2 family?

Answers assume **HD 2021–2024 core+raw still exist**. They do **not** assume a 2026 PBP file (none in the Aug 13 inventory).

| Need | Owned path | Gap |
| --- | --- | --- |
| True pace; plays/game | Count `scrimmage_play` / `pass`+`rush` by `game_id`+team. Garbage weights + `start.TimeSecsRem`+`half` for competitive pace. | No pre-built pace mart. Clock is **half-seconds**, not game clock. |
| Success rate | **`EPA_success` in core** (offense created / defense allowed by flipping `pos_team`). | Null rate unknown. Not opponent-adj unless efficiency parquet is used. |
| EPA | **`EPA` / `EP_start` / `EP_end` in core.** Efficiency builder already emits raw + shrunk opponent-adj. | Adj mart is HD-only, not in git. |
| PPA | **Not in core-31.** Not referenced by ingest keep-list. | CFBD `/ppa` (or equivalent). Do not treat EPA as PPA. |
| Explosive created/allowed; rush/pass explosiveness | Code already: `EPA≥1.0` **or** `statYardage≥15`, split by `pass`/`rush`. Allowed = opponent’s created. | Yard/EPA thresholds are Kos knobs, not a vendor iso-explosion. |
| Early / standard / passing-down efficiency | `down` + `distance` in core. Standard defs (1st/2nd early; 2nd+long / 3rd–4th passing) are reproducible. | No pre-built down-split mart. |
| Sacks | `type.text` parse (and likely a raw boolean among the 477). | Raw flag **unconfirmed** (477 names not stored). |
| TFL | `stuffed_run` is rush-stuff only. Pass TFL would be a yardage proxy. | Official TFL **not in core**. |
| Turnover pressure | Interception / fumble language in `type.text`. | Forced-fumble / pressure charting not in core. |
| Havoc-like | Bill C havoc needs TFL + FF + INT + **PBU**. PBU is not an ESPN PBP field. | **PBU / official havoc = external** (CFBD advanced). |
| Scoring opportunities; PPO / finishing | Drives via `drive.id`; reach via `start.yardsToEndzone` / `rz_play`; finish via scoring `type.text`. | No official drive-result / drive-points column in core. Reproducible only with an explicit opportunity definition. |
| Field position; drive efficiency | `start.yardsToEndzone` is play-level field position. Drive start = first play of `drive.id`. | Drive-efficiency formula not materialized. |
| Off/def current-season rolling form | Historical W−1 form: `efficiency_adj.week_snapshots` uses **same-season `week < W`**. | **No 2026 PBP in the owned inventory.** Score-residual in-season updater is **not** EPA form. |

---

## 5. Feature classification

One class per row. Evidence is one line. HD-conditional rows are marked †.

| Feature | Class | Evidence |
| --- | --- | --- |
| True pace; plays/game | **OWNED_DERIVABLE** † | Core has `scrimmage_play` / `pass` / `rush` / `game_id` / clock / score; no pace column stored. |
| Success rate | **OWNED_DIRECT** † | Core column `EPA_success`; used as-is by `efficiency_adj`. |
| Offensive / defensive EPA | **OWNED_DIRECT** † | Core column `EPA`; week snapshots + adj already implemented. |
| PPA | **NEED_EXTERNAL** | Not in core-31 or ingest keep-list; CFBD PPA is the documented optional source. |
| Explosive-play rate created/allowed; rush/pass explosiveness | **OWNED_DERIVABLE** † | Derived in `efficiency_adj` (`EXPLOSIVE_EPA=1.0`, `EXPLOSIVE_YARDS=15`, pass/rush splits). |
| Early / standard / passing-down efficiency | **OWNED_DERIVABLE** † | Core `down` + `distance`; no stored down-split table. |
| Sacks / turnover pressure (PBP-parse) | **OWNED_DERIVABLE** † | Core `type.text` (and likely raw flags among 477 unlisted cols). |
| Official TFL + charted havoc (incl. PBU) | **NEED_EXTERNAL** | PBU / official TFL / FF not in core; CFBD advanced (or equivalent) required for havoc-as-published. |
| Scoring opportunities; points per opportunity / finishing | **OWNED_DERIVABLE** † | `drive.id` + `start.yardsToEndzone` + `rz_play` + scoring `type.text`; drive points not a core column. |
| Field position; drive efficiency | **OWNED_DERIVABLE** † | `start.yardsToEndzone` is in core (direct yards-to-goal); drive efficiency is an aggregation, not a stored mart. |
| Off/def **historical** rolling form (2021–2024 W−1) | **OWNED_DERIVABLE** † | `week_snapshots`: `feature_week = max week < W`; leakage test in code. |
| Off/def **2026 current-season** rolling form from PBP | **NEED_EXTERNAL** | 2026 PBP not in the 2026-08-13 warehouse inventory; in-repo form is SP+ carry + score residuals. |
| Column-level missingness / raw-477 sack·TFL flags | **UNSAFE_OR_UNKNOWN** | Parquet not on this disk; 477 names never committed; null rates never measured. |

**User-bullet rollup (9 requested features → one class each, weakest honest class when mixed):**

| # | Requested feature | Class |
| ---: | --- | --- |
| 1 | True pace; plays/game | OWNED_DERIVABLE † |
| 2 | Success rate | OWNED_DIRECT † |
| 3 | Off/def EPA **or** PPA | **NEED_EXTERNAL** for the *or PPA* clause; EPA alone is OWNED_DIRECT † |
| 4 | Explosive created/allowed; rush/pass explosiveness | OWNED_DERIVABLE † |
| 5 | Early/standard/passing-down efficiency | OWNED_DERIVABLE † |
| 6 | Sacks/TFL/turnover pressure and havoc-like | **NEED_EXTERNAL** (havoc/PBU / official TFL) |
| 7 | Scoring opportunities; PPO / finishing | OWNED_DERIVABLE † |
| 8 | Field position; drive efficiency | OWNED_DERIVABLE † |
| 9 | Off/def current-season rolling form | **NEED_EXTERNAL** (2026 PBP absent) |

† = class holds only if the Aug 13 HD parquet is still intact.

---

## 6. Point-in-time / W−1 safety

Warehouse contract (sticky): predicting game G may only use rows with `available_at` **strictly before kickoff**. Fallbacks: `available_at.date < game_date`, else `feature_week < game_week`. Unprovable timestamps are **not available**.

| Rule / path | W−1 safe? | Leakage note |
| --- | --- | --- |
| `efficiency_adj.week_snapshots` | **Yes, if used as written** | Week W uses only same-season plays with `week < W`. `assert_no_future_weeks` rejects `max_week_included ≥ as_of_week`. |
| Team-game `available_at` | **Mostly** | Set to kickoff **+ 4 hours** (`GAME_COMPLETE_BUFFER`). Safe for *next* week; unsafe if someone joins same-week later kickoffs without the week filter. |
| Core PBP `available_at` (feature registry) | **Play wallclock** | Registry says game G may only use **prior games**. Same-game future plays must not enter a pre-kick feature. |
| Season-final efficiency | **Unsafe inside that season** | Explicitly forbidden. Finals are for **next year’s prior only**. |
| Packaged SP+ 2025→2026 carry | **OK as 2026 preseason prior** | Prior-year ratings. **Unsafe** as “2026 current-season form.” This report did not open 2025 PBP. |
| In-season score-residual updater (`in_season_update`) | **Not PBP W−1 form** | Uses final margin vs model. Can leak if a same-week result is applied before that week’s remaining kickoffs. |
| 2026 current-season PBP features | **Cannot be proven from owned data** | No 2026 PBP file in the owned inventory. Any 2026 EPA/success/pace/havoc number today would be external or invented. |
| Conference map `season=0` | **Not a history** | 2026 packaged affiliations back-applied. Do not treat as realignment-safe SOS. |
| Odds lake close | **Designed PIT** | Last owned snap **strictly before kickoff**. Close ≠ lock when densify is sparse. |

**2026 W−1 implication:** owned historical PBP can inform *priors and backtests*. It cannot, by itself, produce leakage-safe **2026 through W−1** EPA / success / pace / explosiveness / havoc. That slice is the live CFBD (or SDV re-ingest of **2026 only**) gap — not a reason to buy a new historical vendor.

---

## 7. Smallest remaining external-data requirement

Do **not** buy a Starter Pack. Do **not** replace SportsDataverse. CFBD API stays the live option.

What is **not** required from a new vendor if the HD 2021–2024 PBP is intact:

- Historical PBP for 2021–2024
- Historical EPA / success / down / yardage / play-type / field position
- A second play-by-play product

What CFBD API (existing, auth-fix only) would still need to supply:

- **2026 plays (and/or drives) through W−1** — current-season pace, success, EPA-or-PPA, explosiveness, down splits, field position, rolling form. Point-in-time: games with `week < W` only.
- **PPA** (team and/or play) if Data Layer v2 requires PPA rather than SDV EPA.
- **Advanced defensive / havoc components** CFBD already publishes (TFL, PBU, INT, FF) if havoc is defined as the published rate rather than a `type.text` proxy.
- **Optional already-coded overlays** (not blockers for the PBP layer): `/player/returning`, `/player/portal`, `/recruiting/teams`, `/ratings/sp` — last roster pack ran `--skip-cfbd`.

What is **ops verification**, not an external purchase:

- Confirm the Aug 13 files still exist on `/Volumes/KosEdgeData` (or that they were lost after the 2026-09-03 “lake absent” runner). This inventory does not re-download.

Postgres `cfb_wh_*` being empty does **not** create a purchase need; bulk SoT was parquet on HD.

---

## 8. STOP

Inventory complete.

- No model was fit.
- No scoring equation was changed.
- No 2025 data files were opened.
- No missing features were filled.
- No vendor was searched or purchased.
- No ingest was run.
- No implementation follow-up is authorized by this document.

**STOP.**
