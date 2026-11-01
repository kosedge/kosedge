# CURSOR ADDENDUM t5119u R2-A — outcome-blind owned coverage

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · Paper≠EXEC · no EVAL claim
Authority: OWNER_CLEAR **9103dcff** · COS_ORDER_CURSOR R2A **b2728333** · preflight **b8a1f7b9**
HARD END 00:35 UTC Nov 2 · this file is the ops seal path for Part A.

**Preserve:** t5116u FAILED look is SPENT (result **be409f70** · ONE_RUN **96478f6b** · bind 39909c61). This branch does **not** continue PR #692 / tip `61436fdb` / `f10abd94`. No reset, retry, re-bind, or overwrite of that ONE_RUN/result.

## First-milestone receipt — source / identity / access

| Check | Result |
|---|---|
| Worker | Ryans-MacBook-Air.local · cursor-agent-worker-c8e3b0bf9f |
| Volume | `/Volumes/KosEdgeData` mounted |
| SQLite RO | `/Volumes/KosEdgeData/clean/odds/gapfill/odds_gapfill.sqlite` · 13 877 006 336 bytes · tables `lines`, `requests` · unique index `uq_gapfill_lines` starts with `sport_key` · opened `mode=ro` only |
| Workspace | writable · extracts staged only under `.cos-work/t5119u_r2/` |
| Security | unchanged · Run Everything **not** enabled |
| Branch | **new** `cursor/t5119u-r2a-owned-coverage-c2e1` from `origin/restore-working-ui` @ `5bcb6e88e` |
| t5116u artifacts | not rewritten · parent FAILED files remain on their own branch |
| Protected seasons | 2024–26 JSONL / lake parquet / raw hist **not opened** (directory names only for raw parent listing) |
| Credentials / pulls | none |
| Scoring / forecast / weights | none |
| CERT | 0 · DRAFT≠merge |

## Owned source inventory (approved stores)

t5116u quote manifest **6a1c1b37** (`data/ops/nfl-odds-reader-2020-2023-join-manifest.json`, re-hashed here = match) used **JSONL 2022–23 + open_close CSV 2022–23 only**. Gapfill SQLite was inventoried earlier but **not loaded** by `run_nfl_eval_one_exec_t5116u.py`. R2-A inventories the full owned approved set.

| Store | Path | Bytes | sha256 | Used in 6a1c1b37 load? |
|---|---|---|---|---|
| JSONL 2020 | `/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2020-20260806.jsonl` | 1 010 737 | `9716af4548c1c6c61e66c1f787f0034f008801aa18a057adce64280c8bc854ed` | no (file present; t5116u loaded 2022–23 only) |
| JSONL 2021 | `/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2021-20260806.jsonl` | 1 153 810 | `4e3f9f789f5413cfe941e54f23daadf6429c8771d8514380fbd87e2e7de32036` | no |
| JSONL 2022 | `/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2022-20260806.jsonl` | 1 242 382 | `973c327fa65045698b5f278f4b324b61feeb09d39a93de73e140a15a83484ad7` | **yes** |
| JSONL 2023 | `/Volumes/KosEdgeData/clean/odds/nfl/snapshots-2023-20260806.jsonl` | 3 533 310 | `fe35b2cc48240eccdddba736404f0d9cc1266c32b2177ece7f4484231c4bbbc5` | **yes** |
| open_close CSV | `/Volumes/KosEdgeData/clean/odds/americanfootball_nfl/open_close/lines.csv` | 1 078 200 270 | `ed072346d4a59a995817831f8308647c559f0ac2d820bb3469bce01d3d9d2745` | **yes** (2022–23 commence window) |
| gapfill sqlite | `/Volumes/KosEdgeData/clean/odds/gapfill/odds_gapfill.sqlite` | 13 877 006 336 | original untouched; extract `96c679d73abb16c54dd9de3b0f1844855708dfb1c898864098d7739aaa7b88f0` (19914 rows) | **no** (R2 expansion; same 720 events as CSV mainline) |
| lake parquet 2020–23 | `/Volumes/KosEdgeData/clean/odds/nfl/lake/snapshots-202{0,1,2,3}.parquet` | 47 834 / 88 054 / 79 480 / 64 705 | `b63ebc17…` / `52eaa7d8…` / `458e4951…` / `1cc89168…` (full in `EXTRACT_HASHES.json`) | no (compact lake files; inventory.json also lists 2024–25 keys — those parquet files were **not** opened) |
| lake inventory | `/Volumes/KosEdgeData/clean/odds/nfl/lake/inventory.json` | — | as_of 2026-08-19 · source `/tmp/nfl_oc_lines.csv` | no (counts only; not a quote feed) |
| raw hist 2020–23 | `/Volumes/KosEdgeData/raw/odds/americanfootball_nfl/historical/{2020,2021,2022,2023}` | 8 / 50 / 145 / 935 files | file-count inventory only | no (Odds API harvest JSON; overlap with sqlite/CSV; not a second feed until extract+TZ sealed) |

JSONL schema (2022 sample): `home,away,game_date,captured_at,book,market,spread_home,price_home,price_away,over_price,under_price,total_points,source`. `captured_at` carries an explicit offset (`-04:00`/`-05:00`). **No `event_id` / `commence_time`.** `source=the-odds-api-historical-enterprise`. Home/away are abbreviations (`LA` = Rams).

CSV / sqlite schema: `sport_key,event_id,commence_time,home_team,away_team,snapshot_kind,snapshot_ts,book,market,outcome,price,point`. `commence_time` and `snapshot_ts` are `…Z` (explicit UTC). Outcome-flattened (one row per side).

## Identity pins (outcome-blind)

Copied from spent t5115u/t5116u metric file for **identity only**. Outcomes / scores were not joined.

| Cohort | n | sha256 |
|---|---|---|
| EVAL 2022–23 REG | 449 | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| DEV REG 2020–21 | 437 | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| NON_REG_WILDCARD | 6 | `f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722` |
| games.csv pin | 2992 rows / 1123 in 2020–23 | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` |

Kickoff contract: `games.csv` `kickoff_utc` is explicit `Z`. `schedule_results_2020_2023.csv` `start_time_raw` is **naive** and is **not** used as kickoff or cutoff. PBP `start_time` is **not** used.

Local pins (not a t5116u rewrite): `.cos-work/t5119u_r2/pins/COHORT_IDENTITIES_t5119u.json`, `TARGET_GAMES_892.json`, `GAMES_2020_2023_IDENTITY.json`.

## Frozen time / sign / identity (refuse undocumented)

Observation time ≠ file mtime ≠ import time ≠ `close_*` snapshot label.

| Clock | Field | Allowed use |
|---|---|---|
| Observation | JSONL `captured_at` (offset required) · CSV/sqlite `snapshot_ts` (`Z` required) | KO−60 / ≤24h age |
| Event start | CSV/sqlite `commence_time` (`Z`) vs games `kickoff_utc` (`Z`) | identity for flattened stores; **exact datetime match** |
| Local gameday | JSONL `game_date` vs games `nflverse_gameday` | identity for JSONL only (JSONL has no commence) |
| File / harvest | JSONL filename season, CSV path, sqlite import, lake `as_of` | **not** observation, **not** kickoff |
| Snapshot kind | `mid` / `pre1d` / `pre3d` / `pre7d` / `close_*` | provenance label only; `close_*` is **not** auto-substituted as the KO−60 quote |

Sign: Odds API home handicap, home-negative when home favored. Home margin = −home handicap. Flattened rows must identify the home-team outcome by resolved team name; a lone away-side `point` is **not** silently treated as `spread_home`. Unresolved TZ / sign / team / 0-or-many game matches → refuse that row.

Parser pin (copied reader, not modified originals): `scripts/nfl/t5119u_r2a/nfl_odds_reader.py` sha256 `7bc21d82c1c332eb9ad4e5ba773ecb1bc49cac2ed23f970ab89ec0f9ea591f0e` (same bytes as the t5116u-era reader). Coverage builder hashes into `PARSER_VERSION.json` when sealed.

## Source-selection + dedupe (frozen; not performance-selected)

1. Stores: JSONL 2020–23 + open_close CSV 2020–23 + gapfill sqlite 2020–23 NFL. No 2024–26. No new pulls.
2. Books: **all** admissible `draftkings` and `fanduel`. Do not drop a book because it looks worse. Other books inventoried but not selected.
3. Markets for this coverage freeze: mainline `spread` / `h2h` (`moneyline`) / `total`. Props / periods / alternates are not coverage-eligible.
4. Window: `captured_at ≤ kickoff_utc − 60 minutes` and age ≤ 24h. Missing/naive timestamp → refuse.
5. Duplicate collapse: identical fingerprint `(game_id, book, market, captured_at, outcome, line, price)` keeps one. Same key with conflicting line/price → **refuse** that slot (no majority vote, no “pick the better number”).
6. Per `(game_id, book, market)` keep the latest remaining observation still ≤ cutoff.
7. Across stores, identical fingerprints collapse; conflicts refuse. No source is preferred because it “covers more EVAL games.”
8. A game is coverage-positive for **margin** when ≥1 admissible DK/FD mainline spread remains after collapse. Missing market is labeled missing — not imputed.

## t5116u 132/449 — reproduced, not re-bound

Spent look untouched (ONE_RUN **96478f6b**). Outcome-blind replay of the **same source subset** (JSONL 2022–23 + open_close CSV 2022–23, no sqlite) reproduced **132 / 449 = 47 + 85**. `T5116U_REPLAY.json` `reproduced_spent_132=true`.

| Season | Declared PBP REG den | Replay quote-eligible | Excluded | Rate | G5 HOLD (>30%) |
|---|---|---|---|---|---|
| 2020 | 256 | 0 (not in t5116u load) | 256 | 100% | yes (DEV, not scored) |
| 2021 | 272 | 0 (not in t5116u load) | 272 | 100% | yes (DEV, not scored) |
| 2022 | **271** | **47** | **224** | **82.66%** | **YES** |
| 2023 | **272** | **85** | **187** | **68.75%** | **YES** |

Exact lists: `T5116U_EXCLUSION_REPORT.json` / `T5116U_REPLAY.json` (`matched_game_ids`, `missing_game_ids`, `replay_missing_2022` n=174, `replay_missing_2023` n=143 vs EVAL 449).

### Why those 317 EVAL games were out (source / season / reason)

t5116u `load_quotes` never opened sqlite or 2020–21 files. Replay join tallies on that subset (EVAL games as the only cutoff-bearing identities):

| Reason | n | Meaning |
|---|---|---|
| `missing_cutoff` | 177635 | quote did not match an EVAL identity (other games / no cutoff row) |
| `incompatible_market` | 161194 | props / periods / non-mainline |
| `quote_too_old` | 3609 | observation older than 24h before KO−60 |
| `book_not_benchmark` | 1763 | not DK/FD |
| `post_cutoff` | 614 | `captured_at` after KO−60 |
| `kept_latest` then no spread | remainder of 317 games | identity matched but no admissible DK/FD **spread** after latest-slot collapse |

Per-source EVAL margin after **this** freeze’s documented home-side sign rule (not loosened to chase 132):

| Store | EVAL matched | 2022 | 2023 | Notes |
|---|---|---|---|---|
| JSONL | 95 | 23 | 72 | 2022 JSONL capture ends 2022-12-29; mid-season sparse |
| open_close CSV | 27 | 27 | 0 | 2023 CSV mainline failed exact `commence_time == kickoff_utc` or home-side flatten |
| gapfill sqlite | 27 | 27 | 0 | same 720 events / 19914 DK+FD mainline rows as CSV (`mid/pre1d/pre3d/pre7d` only) |
| Union after conflict-refuse | **95** | (see lists) | (see lists) | 480 CSV↔sqlite slots refused; not loosened |

JSONL+CSV-only documented-sign union was 119. Adding sqlite (byte-identical store to CSV for these IDs) created 480 unresolved fingerprint conflicts; frozen rule refuses those slots. **G5 / KO−60 / ≤24h / DK+FD were not loosened.** t5116u replay remains 132.

All 317 replay-missing EVAL ids carry reason `no_admissible_dk_fd_spread_after_identity_cutoff_age` in `per_game`. Full ids in the JSON report.

## R2-A coverage freeze — SEALED (JSONL + CSV + sqlite)

`COVERAGE_MANIFEST.json` file sha `bfcf8ff4…` · reader `7bc21d82…` · builder `546f60ba…` · CSV `ed072346…` · sqlite extract `96c679d7…` (19 914 rows).

Sqlite extract (t5129u resume, same 1307 IDs, no restart-from-zero, no 2025 dense):

| | |
|---|---|
| event_ids queried | **1307** (720 CSV ∪ 992 request hashes) |
| event_ids with kept DK/FD mainline | **720** |
| request-only IDs with no kept row after book/market/2020–23 filter | 587 |
| rows | **19914** = CSV DK/FD mainline count (3188/5966/4586/6174 by season) |
| books | DK 12406 · FD 7508 |
| snapshot kinds | mid 4894 · pre1d 4894 · pre3d 4656 · pre7d 5470 |
| `dense` 2025 | **not opened** |

| Cohort | n | R2 matched (union, documented sign, conflicts refused) | Missing |
|---|---|---|---|
| EVAL fac21ebe | 449 | **95** | 354 |
| DEV REG 92b91585 | 437 | **72** | 365 |
| NON_REG_WILDCARD f81d381e | 6 | **6** | 0 |

Admissible latest quotes: `ADMISSIBLE_QUOTES.jsonl` n=1475 sha `75c0b14c…`. Collapse: 3689 → 1475, identical dups 571, **conflicts 480 (refused)**. Observation = `captured_at` / `snapshot_ts` with offset/Z.

## R2-B consume (t5125u / t5129u)

`data/ops/nfl-t5119u-r2-owned-coverage/R2B_CONSUME.json` flipped because the freeze is complete.

| Field | Value |
|---|---|
| `market_e2e` | **READY_FOR_R2B_DEV_E2E** |
| sqlite extract | 19914 rows · `96c679d7…` |
| g5_loosened / time_rule_loosened / book_rule_loosened | **false** |
| eval_claim | **false** |
| CERT | 0 |

First DEV eligible id is in `DEV_MATCHED_GAME_IDS.json` — not claimed here. No EVAL scoring.

## Status

- Extract **finished** 1307/1307 · re-seal **done** · #694 updated.
- t5116u 132 reproduced. Conflicts refused. No G5 loosen. No ONE_RUN. No PE. No merge.

CERT=0 · DRAFT≠merge · failure of t5116u ≠ second look.
