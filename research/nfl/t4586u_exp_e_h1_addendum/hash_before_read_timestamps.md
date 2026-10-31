# H1 hash-before-read logs (BOTH runs) — timestamps

**CERT=0 · Exp E addendum only · sealed PASS artifacts not rewritten**

Raw logs have no per-line clock (stdio tee). Timestamps below are **file mtime/ctime in UTC** plus **strict log order**: every `[h1] sha256` line appears **before** the first `[pbp] load` line.

## FAIL run (script `3abbcb90` / `3e71aa00`)

| event | timestamp UTC | sha8 / note |
|---|---|---|
| `games.csv` written + hashed | 2026-10-28T12:33:56Z | **4fe1cdd7** (mtime of `walkforward_games_82ffb211.csv`) |
| PBP 2012 written + hashed | 2026-10-28T12:33:56Z | **447b9078** |
| PBP 2023 written + hashed | 2026-10-28T12:33:59Z | **bd348473** |
| `[h1] wrote SHA256SUMS n=15 (before any input parse)` | after last PBP hash, **before** `[pbp] load 2012` | log line order |
| first `[pbp] load 2012` | after SHA256SUMS write | first parquet read |
| FAIL log closed | 2026-10-28T12:34:01Z | tee mtime `exp-e-audit.log` |
| first-run `counts.json` | same run | **55e3430d** · `n_kickoff_unknown=8` · verdict FAIL |

Verbatim: `fail_run/exp-e-audit.log`

Hash-before-read excerpt (order is the proof):

```
[h1] sha256 games.csv 4fe1cdd7 bytes=1875548
[h1] sha256 historical_oos_games.csv 1ee90fac bytes=758703
[h1] sha256 rolling_features_weekly_pbp_strict_asof_2013_2023.csv 1b07654e bytes=823791
[h1] sha256 play_by_play_2012.parquet 447b9078 bytes=19322039
… 2013–2022 …
[h1] sha256 play_by_play_2023.parquet bd348473 bytes=20534088
[h1] wrote /workspace/research/nfl/t4586u_exp_e_kickoff_asof/SHA256SUMS n=15 (before any input parse)
[pbp] load 2012 bytes=19322039
```

## PASS run (script `c9844c9e` = tip `d7cc7d95` / `7fb6cf19`)

| event | timestamp UTC | sha8 / note |
|---|---|---|
| cache-hit `games.csv` re-hashed | 2026-10-28T12:33:56Z (bytes unchanged) | **4fe1cdd7** |
| cache-hit PBP 2012–2023 re-hashed | 2026-10-28T12:33:56Z–12:33:59Z | same 12 sha8s |
| rolling re-extracted via `git show` | 2026-10-28T12:35:37Z | **1b07654e** (same bytes) |
| `[h1] wrote SHA256SUMS n=15 (before any input parse)` | before first `[pbp] load` | log line order |
| first `[pbp] load 2012` | after SHA256SUMS write | first parquet read this run |
| PASS log closed | 2026-10-28T12:35:40Z | tee mtime `exp-e-audit-rerun.log` |
| sealed PASS `counts.json` | run_id `…20261028T123537Z` | **b0365365** · `n_kickoff_unknown=0` |

Verbatim: `pass_run/exp-e-audit-rerun.log`

```
[h1] cache hit walkforward_games_82ffb211.csv bytes=1875548
[h1] sha256 games.csv 4fe1cdd7 bytes=1875548
[h1] sha256 historical_oos_games.csv 1ee90fac bytes=758703
[h1] sha256 rolling_features_weekly_pbp_strict_asof_2013_2023.csv 1b07654e bytes=823791
[h1] cache hit play_by_play_2012.parquet bytes=19322039
[h1] sha256 play_by_play_2012.parquet 447b9078 bytes=19322039
…
[h1] wrote …/SHA256SUMS n=15 (before any input parse)
[pbp] load 2012 bytes=19322039
```

## Identity

All 15 **input** sha8s are byte-identical across FAIL and PASS (`h1_hash_compare.json` · `IDENTICAL_INPUTS`). No BLOCKED. No re-run.

PBP parquet bytes are attested by these logs; not re-uploaded (~230MB).
