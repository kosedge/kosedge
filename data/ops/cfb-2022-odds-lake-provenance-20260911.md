# 2022 CFB odds-lake provenance — where the 2026-08-13 export was created

**Date:** 2026-09-11  
**Scope:** locate the authoritative tape. No model / coefficient / gate / close-contract / public-CFB change.  
**Decision:** **STOP** — artifact not present on this VM. Train-0 lake close+actual remains **0**. Deficit **700**.

## Authoritative artifact

| Field | Value |
| --- | --- |
| Path | `/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet` |
| Sidecar | `/Volumes/KosEdgeData/clean/odds/cfb/inventory.json` |
| Export as_of | **2026-08-13** |
| Source label | `odds_snapshots postgres (the-odds-api-historical-enterprise)` |
| Documented 2022 snaps | **28,322** |
| Documented close spreads (lake + SDV fill) | **838** |
| Documented lake-primary | **717** |
| Documented warehouse games | **900** |
| Documented FCS-flagged | **119** |
| Checksum in repo | **none** — inventory has counts only, no sha256 |

Committed inventory (not the parquet): `data/ops/cfb-historical-warehouse-v1-20260812-inventory.json`  
Writeup: `data/ops/cfb-historical-warehouse-v1-20260812.md`  
PR that created the contract: **#215** (`feat/cfb-historical-warehouse-v1`, merged 2026-08-13). Bulk parquet was **explicitly not git**.

## Where it was created (DSN + machine)

This was a **developer-Mac** job, not Railway and not this cloud VM.

1. **Populate Postgres** — `scripts/odds/enterprise_training_pull.py`  
   - Hardcoded DSN: `postgresql://ryankos:postgres@127.0.0.1:5432/kosedge`  
   - Usage line in-file: `/Users/ryankos/kosedge/.venv/bin/python3 …`  
   - CFB plan: `americanfootball_ncaaf`, window including `2022-08-27` → `2023-01-09`  
   - Checkpoint: `cfb:mainlines` completed **2026-07-28T02:40:43Z** (840 dates)  
   - Persist target: local `odds_snapshots` with source family `the-odds-api-historical-enterprise`

2. **Export parquet** — `export_odds_lake()` in `cfb_warehouse/odds_lake.py`  
   - Invoked by `scripts/cfb/ingest_historical_warehouse.py`  
   - Reads the same local DSN (`LOCAL_DSN` or `DATABASE_URL`)  
   - Writes `snapshots-{year}.parquet` to `/Volumes/KosEdgeData/clean/odds/cfb/` when the HD is mounted  
   - SQL filter: `leagues.code = 'cfb'` (exact historical export contract)

3. **Owner of the archive** — ops copy is explicit:  
   - `data/ops/cfb-official-slate-model-brief-20260817.md`: “`/Volumes/KosEdgeData/raw/odds/**` (Mac owns archive)”  
   - `data/ops/nfl-camp-monday-refresh-20260817.md`: same Mac-owns-archive rule  

Railway production Postgres is a **different** database. The enterprise pull does not write to Railway. This VM has no `DATABASE_URL` and `/Volumes/KosEdgeData` is not mounted.

## Searched this run (not found)

| Location | Result |
| --- | --- |
| `/Volumes/KosEdgeData/**` | volume absent |
| `data/cfb/warehouse/clean/odds_cfb/` | empty (gitignored) |
| workspace / `/mnt` / `/cursor/stores` / `/tmp` | no `snapshots-2022.parquet` |
| git history / LFS / GitHub Actions artifacts | none |
| Google Drive | no matching file |
| Notion | no lake parquet |
| Cloudflare R2 bindings | not authenticated |
| `DATABASE_URL` / `WAREHOUSE_DATABASE_URL` | unset |
| local `127.0.0.1:5432` | no Postgres on this VM |
| Railway secrets | names only; cannot export |

No historical sha256 exists to validate against. Count SoT remains the 2026-08-13 inventory.

## How to put the tape on this (or any) agent

On the Mac, with KosEdgeData mounted — **copy the owned file**, do not live-densify The Odds API:

```bash
ls -l /Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet
# expected: one parquet used by the 2026-08-13 inventory (28,322 rows)

# optional re-export from the same local DB that created it
# DATABASE_URL=postgresql://ryankos:postgres@127.0.0.1:5432/kosedge
# python scripts/cfb/ingest_historical_warehouse.py --seasons 2022 --skip-pbp
```

Place `snapshots-2022.parquet` at either:

- `/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet` (canonical), or
- `data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet` (repo fallback)

Then re-run `python3 scripts/cfb/recover_cfb_2022_closes.py`. If Train-0 lake close+actual **n ≥ 700**: **GO TO FROZEN 1.40 SCORING** and stop. Do not score until that verify.

## Funnel this VM (unchanged)

raw snaps **0** → valid pregame closes **0** → matched games **0** → FBS/FBS **0** → actual available **0** → Train-0 close+actual W1–14 **0**

Reason codes: `LAKE_NOT_MOUNTED` / `NO_LAKE_MATCH` on all 900 warehouse games. SDV fill is not a substitute (125 lined, 119 FCS, 6 FBS/FBS, 1 Layer-A-both).

Gate retained at 700. Actuals-only not adopted. Frozen 1.40 not scored. CFB dark. No PLAY.
