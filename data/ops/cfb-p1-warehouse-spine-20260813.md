# CFB P1 warehouse spine — immutable fairs + coverage

**Date:** 2026-08-13  
**Branch:** `feat/cfb-p0-p1-warehouse-spine` → `deploy-vercel`  
**Depends on:** warehouse v1 (#215), efficiency/prior v1, walk-forward W0–4  
**Doctrine:** Zero leakage. Insert-only research snapshots. No KEI. No engine bump. No prior redesign.

P0 audit: `data/ops/cfb-p0-audit-20260813.md`  
Coverage JSON: `data/ops/cfb-p1-coverage-20260813.json`

## What already existed vs new

| Already existed (2026-08-12) | New this PR |
| --- | --- |
| `cfb_warehouse/` leakage, ingest, odds_lake, pbp, identity, backtest, walkforward, prior, efficiency | `predictions.py` — immutable JSON/JSONL/parquet writer |
| `infra/db/051_cfb_historical_warehouse.sql` (`cfb_wh_*` games/odds/registry) | `052_cfb_warehouse_spine.sql` — `model_predictions`, `backtest_runs`, coach + team-season stubs |
| HD parquet SoT + committed inventories | `scripts/cfb/report_warehouse_coverage.py` |
| `run_walkforward_week0_4.py` (full HD harness) | `scripts/cfb/run_walkforward_dry_run.py` (limit / fixtures / no KEI) |
| Leakage + identity + odds-lake + walk-forward tests | Spine tests: overwrite reject, leakage still holds, coverage dry-run, dry-run writes no KEI |

Ingest / prior / Edge Board / engine version **unchanged**.

## Paths

| What | Where |
| --- | --- |
| Raw SDV / PBP | `/Volumes/KosEdgeData/raw/cfb/{historical,pbp}/` |
| Clean warehouse | `/Volumes/KosEdgeData/clean/cfb/historical/` |
| Odds lake | `/Volumes/KosEdgeData/clean/odds/cfb/` |
| New predictions dir | `{clean}/predictions/{model_version}/{as_of}/{game_id}.json` (+ optional `.jsonl` / `.parquet`) |
| Repo fallback (gitignored) | `data/cfb/warehouse/{raw,clean}/` |
| Postgres | `cfb_wh_*` after `051` + `052` applied. **Not loaded in prod.** |

## Schema (052)

- `cfb_wh_model_predictions` — insert-only. PK `(model_version, as_of, game_id)`. Columns: `fair_spread`, `fair_total`, `wp`, `uncertainty`, plus season/week/teams/`available_at`/`era_tag`/`notes`.
- `cfb_wh_backtest_runs` — harness metadata. Not a KEI publish log.
- Stubs: `cfb_wh_team_seasons` (conference by season), `cfb_wh_coaches`.

**Never UPDATE a research snapshot.** Injury or new information = new row with a new `as_of`. KEI, if it ever exists, is a later reprice — not an in-place edit.

Python writer (`cfb_warehouse.predictions.write_prediction`) rejects overwrite of the same key and requires `model_version` + `as_of` (+ `game_id`). If `available_at` is present it must pass `strictly_before_kickoff`.

## How to re-ingest / report

```bash
# existing warehouse (HD)
python scripts/cfb/ingest_historical_warehouse.py
python scripts/cfb/ingest_historical_warehouse.py --skip-pbp

# coverage (works without HD — committed inventories)
python scripts/cfb/report_warehouse_coverage.py --dry-run --no-hd
python scripts/cfb/report_warehouse_coverage.py

# walk-forward dry-run (no KEI; fixtures if parquet missing)
python scripts/cfb/run_walkforward_dry_run.py --limit 8
python scripts/cfb/run_walkforward_dry_run.py --fixtures

# full W0–4 (HD)
python scripts/cfb/run_walkforward_week0_4.py --limit 20

# optional later — operational slices only, not a multi-decade Railway reload
# psql "$DATABASE_URL" -f infra/db/051_cfb_historical_warehouse.sql
# psql "$DATABASE_URL" -f infra/db/052_cfb_warehouse_spine.sql
```

## Leakage rules (sticky)

`strictly_before_kickoff`. Fallbacks: `available_at.date < game_date`, else `feature_week < game_week`. Unprovable timestamps are **not** available.

Forbidden as same-season features: final-season ratings, end-of-year SOS, post-hoc recruiting, “what the freshman became”.

## Era tags

Metadata / weighting hooks only. Do not silently drop years.

| Tag | Seasons |
| --- | --- |
| `pre-2002` | < 2002 (not ingested) |
| `2002-09` | 2002–2009 |
| `2010-17` | 2010–2017 |
| `2018-21` | 2018–2021 |
| `2022-present` | 2022+ |

Ingested games are 2020–2025 (`2018-21` + `2022-present`). PBP starts 2014 (`2010-17` onward).

## Metrics scaffold (not a publish bar)

When a research fair is present, grade:

| Metric | When |
| --- | --- |
| MAE / RMSE vs close | `fair_spread` + close spread |
| ATS vs close | model pick vs close; pushes null |
| Totals ATS | `fair_total` + close total (when both exist) |
| Brier / log-loss | `wp` vs home win (when wp present) |
| CLV stub | open **and** close exist; last owned snap ≠ lock |

Walk-forward already emits MAE / ATS / signed CLV stub. Totals ATS + Brier/log-loss are hooks for P2+ — do not invent them from missing wp/totals.

## Slice hooks

Week band (`w0_1` / `w2_4` / `w5_plus`), conference (needs `cfb_wh_team_seasons` filled), favorite size (home fav vs dog). **Flag thin samples honest:** `n < 30` thin, `n < 50` exploratory (existing walk-forward constants). Do not hide a 12-game conference slice as a result.

## Postgres vs HD

HD parquet is SoT for multi-year games / PBP / odds. Postgres is for **operational slices** after 051+052 are applied. **Do not** bulk-reload 174k lake snaps or 1.8M PBP rows into Railway.

## FCS

Keep FCS games (701 flagged). Do not zero them. Separate FCS strength prior is **P2**, not this spine.

## Honesty

No KEI. No Edge Board change. Engine stays `cfb-season-engine-v0.9-inseason`. Prior not redesigned. Early-season fair still does not beat close — dry-run must not be read as a publish.
