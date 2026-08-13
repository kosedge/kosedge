# CFB Historical Warehouse v1 + Zero-Leakage Contract

**Date:** 2026-08-12  
**Branch:** `feat/cfb-historical-warehouse-v1` → `deploy-vercel`  
**Depends on:** 2026 roster refresh live (`as_of=2026-08-12`, PR #214)  
**Doctrine:** Own the data. SportsDataverse / CFBD / cfbfastR are ingest, not the live database. Zero future leakage. No KEI. No UI pass. Do not replace project-game.

Inventory snapshots (committed, small):

- `data/ops/cfb-historical-warehouse-v1-20260812-inventory.json`
- `data/ops/cfb-historical-warehouse-v1-20260812-pbp-inventory.json`

Bulk parquet is **not** in git.

## Smoke (2026-08-12 ingest)

| | Count |
| --- | ---: |
| Teams (engine codes) | 136 |
| Team aliases | 293 |
| Games (STATUS_FINAL, 2020–2025) | **5,196** |
| With kickoff timestamp | **5,196 / 5,196** |
| Closing-line rows | 5,196 |
| With close spread (lake + SDV fill) | **4,994** |
| With open spread (lake) | **4,184** |
| With close ML (lake) | **4,070** |
| Lake-matched games | **4,184** (unmatched 1,012 kept — no silent year drop) |
| Odds API lake snapshots | **174,606** / 4,736 distinct lake games |
| PBP plays (2014–2025) | **1,819,153** |
| PBP games | **10,297** |
| FCS-flagged games | 701 |

### Sample join — game → open/close → result

ESPN `401628323` · 2024 week 1 · Georgia vs Clemson (neutral)

| Field | Value |
| --- | --- |
| `game_id` | `401628323` |
| `kickoff` | `2024-08-31T16:00Z` |
| `home_team_id` / `away_team_id` | `UGA` / `CLEM` |
| Result | 34–3 (home) |
| `open_spread_home` / `close_spread_home` | −13.5 / −13.5 (DK) |
| `open_total` / `close_total` | 49.0 / 48.5 |
| `close_ml_home` / `close_ml_away` | −600 / +440 |
| `open_captured_at` | 2024-08-23 17:53 UTC |
| `close_captured_at` / `available_at` | 2024-08-27 16:54 UTC (**before kickoff**) |
| `book` / `source` / fidelity | draftkings / `odds_api_lake` / `book_timestamped` |
| `n_lake_snaps` | 45 |
| `era_tag` | `2022-present` |

SDV close-ish for this game was −10.5 / 49.5; lake is primary. Close is the last **owned** snapshot strictly before kickoff (densify may not include a true lock).

Harness (`python scripts/cfb/run_warehouse_backtest.py --limit 5`) emits result columns with placeholder fairs (`model_fair_present=false`). 2020 UAB sample now has open −14.5 / close −21.0 for a CLV stub later.

## Schema

### Parquet (SoT for v1)

| File | Grain |
| --- | --- |
| `teams.parquet` | one row per packaged engine code |
| `team_aliases.parquet` | ESPN abbr / ESPN name / packaged alias → `team_id` |
| `games.parquet` | one row per final game (`game_id` = ESPN id) |
| `closing_lines.parquet` | lake primary open/close/ML; SDV fill |
| `odds_snapshots.parquet` | SDV close-ish (fill) |
| `clean/odds/cfb/snapshots-{year}.parquet` | owned Odds API lake |
| `raw/cfb/pbp/play_by_play_{year}.parquet` | full cfbfastR PBP (~477 cols) |
| `clean/cfb/historical/pbp/pbp_{year}_core.parquet` | EPA / success / state subset |
| `inventory.json` | season counts + leakage rule |

### Postgres (DDL only this PR)

`infra/db/051_cfb_historical_warehouse.sql` — `cfb_wh_*` plus feature registry seeds:

- `model_fair_placeholder`
- `pbp_core`
- `odds_api_lake_close`

Not loaded this PR. Season-engine does **not** read these tables per request.

## Placement

| What | Where |
| --- | --- |
| Raw SDV CSVs | `/Volumes/KosEdgeData/raw/cfb/historical/sdv/` |
| Raw PBP | `/Volumes/KosEdgeData/raw/cfb/pbp/` |
| Clean warehouse | `/Volumes/KosEdgeData/clean/cfb/historical/` |
| Odds lake | `/Volumes/KosEdgeData/clean/odds/cfb/` |
| Repo fallback (gitignored) | `data/cfb/warehouse/{raw,clean}/` |
| Postgres metadata | `cfb_wh_*` after `051` is applied |
| Code | `services/model-service/src/services/cfb_warehouse/` |
| Identity SoT | `cfb_warehouse.identity` (hist-cal imports from here) |

## Years covered

| Layer | Years | Notes |
| --- | --- | --- |
| Games + results + kickoff | 2020–2025 | `load_cfb_schedules` equivalent (SDV `espn_cfb_schedules`) |
| Odds API lake (primary) | 2020–2026 | 174,606 snaps; DK/FD; exported from local `odds_snapshots` |
| SDV betting (fill) | 2020–2025 | dense 2023–2025; sparse earlier |
| PBP | **2014–2025** | `load_cfb_pbp`; full + core |
| Pre-2002 | none | era tag exists for later weighting only |

Close/open coverage by season (games kept even when unmatched):

| Season | Games | Close spread | Open spread | Lake primary |
| ---: | ---: | ---: | ---: | ---: |
| 2020 | 571 | 512 | 477 | 477 |
| 2021 | 891 | 814 | 696 | 696 |
| 2022 | 900 | 838 | 717 | 717 |
| 2023 | 911 | 907 | 713 | 713 |
| 2024 | 965 | 965 | 793 | 793 |
| 2025 | 958 | 958 | 788 | 788 |

PBP by season:

| Season | Plays | Games | Raw cols |
| ---: | ---: | ---: | ---: |
| 2014 | 155,521 | 854 | 477 |
| 2015 | 158,501 | 866 | 477 |
| 2016 | 155,622 | 858 | 477 |
| 2017 | 155,505 | 872 | 477 |
| 2018 | 158,249 | 884 | 477 |
| 2019 | 156,888 | 890 | 477 |
| 2020 | 100,420 | 565 | 476 |
| 2021 | 146,367 | 842 | 477 |
| 2022 | 149,654 | 861 | 477 |
| 2023 | 153,626 | 903 | 477 |
| 2024 | 162,950 | 946 | 477 |
| 2025 | 165,850 | 956 | 476 |

## Join keys

| Join | Key | Notes |
| --- | --- | --- |
| games ↔ closing_lines | `game_id` (ESPN) + `season` | inner join; no year dropped |
| Odds API lake | `(game_date, home_name, away_name)` | Odds abbrs (`GEBU`, `FLGA`) are **not** engine codes |
| Lake close | last snap with `captured_at` **strictly before kickoff** | DK then FD |
| Lake open | first snap | same books |
| team identity | `team_id` | packaged engine code (`UGA`, `UF`, `TAMU`) |
| FCS / unmapped | `espn:{espn_team_id}` | `fcs_opponent=true` |
| PBP | `game_id` (ESPN) | core cols include `EPA`, `EPA_success`, `rz_play`, `stuffed_run` |

Spread convention: **negative = home favored** (Odds API / project-game).

## Leakage contract (sticky)

**Rule:** `strictly_before_kickoff`

Predicting game G in season S week W may only use information with `available_at` **strictly before kickoff of G**.

Fallbacks (same spirit, never looser):

1. `available_at.date < game_date`
2. `feature_week < game_week` (NFL KAV-style)
3. Unprovable timestamps → **not available** (null / reject). Do not invent.

Forbidden as same-season feature inputs:

- final-season ratings for season S used inside season S
- end-of-year SOS
- post-hoc recruiting revisions
- “what the freshman became”

Era tags (metadata only in v1): `pre-2002` / `2002-09` / `2010-17` / `2018-21` / `2022-present`.

Enforcement:

- `src.services.cfb_warehouse.leakage.assert_available_before_kickoff`
- harness rejects a model fair whose `available_at` is not strictly before kickoff
- odds-lake reducer drops post-kickoff snapshots (unit test: toy −3 close after kickoff is ignored)
- `.cursor/rules/cfb-historical-warehouse.mdc`

Future preseason prior and opponent-adj efficiency **must** register `available_at`.

## How to re-run ingest

```bash
# games 2020-2025 + odds lake overlay + PBP 2014-2025
python scripts/cfb/ingest_historical_warehouse.py

python scripts/cfb/ingest_historical_warehouse.py --skip-pbp
python scripts/cfb/ingest_historical_warehouse.py --pbp-seasons 2022-2025

python scripts/cfb/run_warehouse_backtest.py --limit 5

cd services/model-service
pytest tests/test_cfb_warehouse_identity.py tests/test_cfb_warehouse_leakage.py \
  tests/test_cfb_warehouse_odds_lake.py tests/test_cfb_season_engine.py -q
```

Ingest uses the repo `.venv` (pandas/pyarrow/psycopg). Odds export reads local `postgresql://ryankos:postgres@127.0.0.1:5432/kosedge` (or `DATABASE_URL`). Production model-service does not import parquet at request time.

Optional later: `psql "$DATABASE_URL" -f infra/db/051_cfb_historical_warehouse.sql`.

## Known gaps

- **1,012 warehouse games unmatched to the lake** (mostly FCS / name mismatches). Rows kept; SDV fill where a close-ish line exists.
- **Lake close ≠ lock** when densify is sparse near kickoff (UGA–CLEM last owned snap is Aug 27 for an Aug 31 kickoff).
- **Conference membership** is the 2026 packaged map (`season=0`). Not a realignment history.
- **Historical rosters** (`load_cfb_rosters`) not materialized this pass — identity is ESPN maps + packaged aliases.
- **Opponent-adj EPA mart** not built (PBP files are the input).
- **CFBD betting** not pulled; lake is primary, SDV is fill.
- **Postgres `cfb_wh_*` empty** until 051 is applied and loaded.
- **Pre-2014 PBP / pre-2020 games** not ingested (schedules exist on SDV back to 2004).

## Honesty / non-goals

- No CFB KEI / Edge Board tags
- No full opponent-adjusted EPA mart
- No portal valuation / PFF
- No UI redesign
- Current project-game / season-engine **unchanged** at request time

## Next (not this PR)

1. Opponent-adj efficiency + garbage-time weights on clean PBP  
2. Preseason prior v1 (program + roster + QB + uncertainty) with `available_at`  
3. Walk-forward vs closes (Week 0–4 emphasis)  
4. KEI only when pure fairs are trustworthy
