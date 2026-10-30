# D-2 contract (implemented in this runner)

IMV `8ca00bc4` D-2 (opening blocker), after Ryan CLEAR `fabf8732`:

> the holdout runner must implement in code, with a fixture for each STOP:
> - the listings zone census (naive STOP);
> - the incomplete-row rule and its count before the join;
> - the observed-id pin into provenance;
> - the on-disk .v2 export pin.

This package implements those four in `run_injury_holdout_d2.py`.
`--mode holdout` dies before any path is opened. No 2024/25 read.

## Pipeline order (fail closed)

1. Refuse any path or row whose season/filename is 2024, 2025, or 2026.
2. Pin the export by the on-disk `.sha256.v2` sidecar (not the blob hash).
3. Census `date_modified` on listings. Any naive / zoneless / empty / other → STOP.
4. Apply the incomplete-row rule. Record `n_incomplete` total and by season,
   and the observed `game_id` set, **before any close/outcome join**.
5. Write those IDs into provenance.
6. `join_close_or_outcome` dies unless steps 3 and 4 have already recorded.
   This package never joins holdout closes.

## STOP fixtures (one each)

| id | fixture | must STOP |
|---|---|---|
| F-NAIVE | `fixtures/naive/` | listings `date_modified` without timezone |
| F-INC-TS | `fixtures/incomplete-ts/` | `complete=false` + a timestamp |
| F-INC-DELTA | `fixtures/incomplete-delta/` | `complete=false` + non-null delta |
| F-COMP-NULL | `fixtures/complete-null/` | `complete=true` + null timestamp |
| F-V2-MISSING | `fixtures/v2-missing/` | no `.sha256.v2` sidecar |
| F-V2-BLOB | `fixtures/v2-blob/` | sidecar is the blob hash |
| F-V2-MISMATCH | `fixtures/v2-mismatch/` | sidecar sha ≠ on-disk sha |
| F-JOIN-FIRST | `fixtures/join-first/` | join called before incomplete count |
| F-NAME | in-memory `listings_2024.csv` | holdout year in path; file is not opened |
| F-HOLDOUT | `--mode holdout` | opening blocked; 2024/25 not opened |

Happy path: `fixtures/ok/` (synthetic) and `--mode le2023` (export `a38a55bb`
+ listings 2013–2023 only).

## Incomplete-row rule (request v3.1 / C-2)

From the **export**, before any outcome or close join:

1. incomplete iff `complete=false`
2. require all five timestamps null and both deltas null
3. complete + null timestamp → STOP; incomplete + timestamp or non-null delta → STOP
4. exclude identically in both arms (applied on the export, before arms split)
5. record `n_incomplete` total and by season; pin the observed `game_id` set
6. do not join close or outcome onto an incomplete row

le2023 observed set (regression pin, from `a38a55bb`):

```
2013_1_CIN_CHI
2013_1_NYG_DAL
2014_15_SF_SEA
2015_1_NO_ARI
2017_1_IND_LA
2020_1_GB_MIN
2020_6_KC_BUF
2022_2_IND_JAX
2022_7_CHI_NE
2022_12_BAL_JAX
2023_5_HOU_ATL
```

11 total; 2013:2, 2014:1, 2015:1, 2017:1, 2020:2, 2022:3, 2023:1.

## Listings TZ census

Zone-bearing = trailing `Z` or a numeric offset. Naive/zoneless = STOP.
`Z` is not reinterpreted as ET. Empty / other = STOP (fail closed).
Census is over every row in the allowed-year files (including playoff
`game_type`). REG filter is a fit concern, not a TZ concern.

## Export pin

On-disk file sha via `{export}.sha256.v2` (`{sha256}  {basename}`).
Blob hash (`.sha256`, JSON without the extra newline) is **not** a pin.
le2023 pin: `a38a55bb`. Blob `46d2a565` is not a pin.

## What this runner does not do

- Open, read, load, or score 2024/25
- Write Ryan or IMV tokens
- Write the once-only lock
- Merge, deploy, or set `NFL_TOTALS_*`
- Build a holdout export
