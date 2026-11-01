# t5098u 11:00 EST checkpoint — Package A (DRAFT only, CERT=0)

**When:** 2026-11-01 ~16:00Z  
**Agent:** https://cursor.com/agents/bc-c81daa8f-cdd3-5efe-b0d2-aed940e417f0  
**Branch:** `cursor/nfl-odds-reader-cutoff-join-17f0`  
**Base:** `origin/restore-working-ui` @ `5bcb6e88e`  
**Tip referenced:** 02ca8367 (not in this git object store; treated as owner CLEAR label, not a checkout)  
**Paid Odds pauses stand:** 783c286f + 0c5c52ab. No collector wait. No merge. No CERT.

## Execution confirmation

KosEdgeData **is mounted** at `/Volumes/KosEdgeData` (APFS `/dev/disk3s2`). Package A proceeded.

First test result (synthetic boundary, no HD required):

```
cd services/model-service && PYTHONPATH=. python -m pytest tests/test_nfl_odds_reader.py -q
...........                                                              [100%]
11 passed in 0.25s
```

Reader/join module: `services/model-service/src/services/nfl_odds_reader.py`  
Tests: `services/model-service/tests/test_nfl_odds_reader.py`

Covered: home/away sign, city-alias ambiguity, post-cutoff rejection (later close not substituted), exact-cutoff eligibility, UTC normalize, identical-dupe keep-one, conflicting-dupe exclude, missing cutoff/book/timestamp, prop/period/line mismatch, 2020–2023 season bound (Feb Super Bowl → prior season).

## First source pin (RO, 2020–2023 only)

| Store | Path | Note |
| --- | --- | --- |
| Primary warehouse | `/Volumes/KosEdgeData/clean/odds/gapfill/odds_gapfill.sqlite` (13,877,006,336 bytes) | Mixed-season file; reader uses `commence_time >= 2020-03-01 AND < 2024-03-01` |
| Isolated clean JSONL | `/Volumes/KosEdgeData/clean/odds/nfl/snapshots-202{0,1,2,3}-20260806.jsonl` | 2024–26 JSONL **not opened** |
| Open/close CSV | `/Volumes/KosEdgeData/clean/odds/americanfootball_nfl/open_close/lines.csv` | Flattened lines; season filter on read |
| nflverse PBP (games) | `/Volumes/KosEdgeData/nflverse/play_by_play_202{0,1,2,3}.csv` | Existing archive; not re-downloaded |
| Lake parquet 2020–23 | `/Volumes/KosEdgeData/clean/odds/nfl/lake/snapshots-202{0,1,2,3}.parquet` | Cited via `inventory.json` by_season keys only; 2024–26 parquet **not opened** |

## First artifact / join result (available at checkpoint; refined after)

Clean JSONL 2020–2023 (files opened; 2024–26 JSONL not opened): **22,078** mainline rows / **1,117** distinct games.

Open/close CSV 2020–2023 stream: **429,642** flattened rows — mainline **126,276** / period **148,682** / props **152,964** / unknown **1,720**.

Cutoff join (CSV mainline, explicit `commence_time`): **95,236** eligible, **190** `post_cutoff` (later close not substituted), **30,850** identical-dupe keep-one.

Tests at checkpoint: **12 passed**.

Full inventory: `data/ops/nfl-odds-reader-2020-2023-inventory.md`  
Join manifest: `data/ops/nfl-odds-reader-2020-2023-join-manifest.json`

13GB sqlite `lines` GROUP BY was started RO with the 2020–2023 commence window; request-ledger counts are already in the inventory. Do not add harvest + lake + jsonl + csv + sqlite into one total.

No scope expansion.
