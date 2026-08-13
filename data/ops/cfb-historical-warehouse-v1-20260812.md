# CFB Historical Warehouse v1 + Zero-Leakage Contract

**Date:** 2026-08-12  
**Branch:** `feat/cfb-historical-warehouse-v1` → `deploy-vercel`  
**Depends on:** 2026 roster refresh live (`as_of=2026-08-12`, PR #214)  
**Doctrine:** Own the data. SportsDataverse / CFBD / cfbfastR are ingest, not the live database. Zero future leakage. No KEI. No UI pass. Do not replace project-game.

Inventory snapshot (committed, small): `data/ops/cfb-historical-warehouse-v1-20260812-inventory.json`  
Bulk parquet is **not** in git.

## Smoke (2026-08-12 ingest)

| | Count |
| --- | ---: |
| Teams (engine codes) | 136 |
| Team aliases | 293 |
| Games (STATUS_FINAL) | **5,196** |
| Closing-line rows | 5,196 |
| Odds snapshots (close-ish) | 5,196 |
| With kickoff timestamp | **5,196 / 5,196** |
| With close spread | **3,106** |
| With open spread / ML | **0** (SDV betting has neither) |
| FCS-flagged games | 701 |
| Season range | **2020–2025** |

### Sample join — game → close → result

ESPN `401628323` · 2024 week 1 · Georgia vs Clemson (neutral, Atlanta)

| Field | Value |
| --- | --- |
| `game_id` | `401628323` |
| `kickoff` | `2024-08-31T16:00Z` |
| `home_team_id` / `away_team_id` | `UGA` / `CLEM` |
| Result | 34–3 (home) |
| `close_spread_home` / `close_total` | −10.5 / 49.5 |
| `open_spread_home` | null (not in SDV) |
| `book` / fidelity | `espn_sdv` / `close_ish_resolved` |
| `era_tag` | `2022-present` |
| `fcs_opponent` | false |

Harness (`python scripts/cfb/run_warehouse_backtest.py --limit 5`) grades result columns with `model_fair_present=false` (placeholder path). Future fairs must stamp `available_at` strictly before kickoff.

## Schema

### Parquet (SoT for v1)

| File | Grain |
| --- | --- |
| `teams.parquet` | one row per packaged engine code |
| `team_aliases.parquet` | ESPN abbr / ESPN name / packaged alias → `team_id` |
| `games.parquet` | one row per final game (`game_id` = ESPN id) |
| `closing_lines.parquet` | one row per game; open/ML null until Odds API lands |
| `odds_snapshots.parquet` | close-ish snapshot at kickoff (`snapshot_kind=close_ish`) |
| `pbp/README.md` | path only — no play-by-play in v1 |
| `inventory.json` | season counts + leakage rule |

### Postgres (DDL only this PR)

`infra/db/051_cfb_historical_warehouse.sql`

- `cfb_wh_ingestion_runs`
- `cfb_wh_teams`
- `cfb_wh_team_aliases` (PK `alias, kind, season`; `season=0` = not year-specific)
- `cfb_wh_games`
- `cfb_wh_odds_snapshots`
- `cfb_wh_closing_lines`
- `cfb_wh_feature_registry` (seed: `model_fair_placeholder`)

Not loaded this PR. Season-engine does **not** read these tables per request.

## Placement

| What | Where |
| --- | --- |
| Raw SDV CSVs | `/Volumes/KosEdgeData/raw/cfb/historical/sdv/` |
| Clean parquet | `/Volumes/KosEdgeData/clean/cfb/historical/` |
| Repo fallback (gitignored) | `data/cfb/warehouse/{raw,clean}/` |
| Postgres metadata | `cfb_wh_*` after `051` is applied |
| Code | `services/model-service/src/services/cfb_warehouse/` |
| Identity SoT | `cfb_warehouse.identity` (hist-cal imports from here) |

HD was mounted for the 2026-08-12 ingest. If unmounted, pass `--repo-fallback`.

## Years covered

| Layer | Years | Notes |
| --- | --- | --- |
| Games + results + kickoff | 2020–2025 | SportsDataverse schedules + box + linescores |
| SDV close spread/total | dense **2023–2025**; sparse 2020–2022 | source gap, not a silent drop |
| SDV open / ML | none | columns absent |
| PBP | none | path reserved |
| Odds API CFB (owned, not copied) | 2020–2026 | 174,606 rows / 4,736 games, DK+FD — JSONL not on `clean/odds/cfb` yet |
| Pre-2002 | none | era tag exists for later weighting only |

Close-spread coverage by season (games kept even when line is missing):

| Season | Games | With close spread | FCS flagged |
| ---: | ---: | ---: | ---: |
| 2020 | 571 | 37 | 34 |
| 2021 | 891 | 122 | 116 |
| 2022 | 900 | 125 | 119 |
| 2023 | 911 | 882 | 116 |
| 2024 | 965 | 965 | 166 |
| 2025 | 958 | 958 | 150 |

## Join keys

| Join | Key | Notes |
| --- | --- | --- |
| games ↔ closing_lines ↔ snapshots | `game_id` (ESPN) + `season` | inner join; no year dropped |
| team identity | `team_id` | packaged engine code (`UGA`, `UF`, `TAMU`) |
| FCS / unmapped | `espn:{espn_team_id}` | `fcs_opponent=true`; Montana stays unmapped |
| Future Odds API overlay | `(game_date, home, away)` then book | do not drop 2020–2022 while overlay is missing |
| Engine codes | same maps as hist-cal | Florida Gators `FLA`→`UF`; Findlay blocked |

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

Era tags (metadata only in v1, for later weighting): `pre-2002` / `2002-09` / `2010-17` / `2018-21` / `2022-present`.

Enforcement:

- `src.services.cfb_warehouse.leakage.assert_available_before_kickoff`
- skeleton harness rejects a model fair whose `available_at` is not strictly before kickoff
- `.cursor/rules/cfb-historical-warehouse.mdc`

Future preseason prior and opponent-adj efficiency **must** register `available_at` (and a `cfb_wh_feature_registry` row).

## How to re-run ingest

From repo root, with HD mounted (or `--repo-fallback`):

```bash
# default seasons 2020-2025; download-once cache under raw/sdv
python scripts/cfb/ingest_historical_warehouse.py

# subset
python scripts/cfb/ingest_historical_warehouse.py --seasons 2022,2023,2024,2025

# skeleton harness (placeholder fairs)
python scripts/cfb/run_warehouse_backtest.py --limit 5

cd services/model-service
pytest tests/test_cfb_warehouse_identity.py tests/test_cfb_warehouse_leakage.py tests/test_cfb_season_engine.py -q
```

Ingest uses the repo `.venv` (pandas/pyarrow). Production model-service does not import parquet at request time.

Optional later: `psql "$DATABASE_URL" -f infra/db/051_cfb_historical_warehouse.sql` then a loader (not this PR).

## Known gaps

- **SDV closes sparse 2020–2022** (37 / 122 / 125). Games and results are kept. Fill from owned Odds API JSONL when copied to HD.
- **No open lines, no moneylines** in SDV betting (9 columns). CLV stub is magnitude-only until opens land.
- **SDV close is close-ish resolved**, not a book-timestamped close. `line_fidelity=close_ish_resolved`.
- **Conference membership** is the 2026 packaged map (`conference_source=packaged_2026_approx`, `season=0`). Not a realignment history.
- **FCS opponents** kept with `fcs_opponent` (hist-cal still drops unmapped for grading).
- **Pre-2002 / 2002–2019 games** not ingested. Schedules exist on SDV back to 2004; v1 default is 2020–2025 to match owned odds years.
- **PBP / EPA mart** not ingested (path only).
- **CFBD / cfbfastR** not pulled this pass (no live query; optional overlay later).
- **Postgres empty** until 051 is applied and loaded.
- **0–0 postponed/canceled** games skipped (`not_final`).

## Honesty / non-goals

- No CFB KEI / Edge Board tags
- No full EPA feature mart
- No portal valuation
- No PFF / Sportradar
- No UI redesign
- Current project-game / season-engine **unchanged** at request time (identity maps moved to warehouse; hist-cal still reconstructs 2022–2025 proxy grades)

## Next (not this PR)

1. Opponent-adj efficiency + garbage-time weights on clean PBP/team stats  
2. Preseason prior v1 (program + roster + QB + uncertainty) with `available_at`  
3. Walk-forward vs closes (Week 0–4 emphasis); land Odds API CFB JSONL for 2020–2022 opens/closes  
4. KEI only when pure fairs are trustworthy
