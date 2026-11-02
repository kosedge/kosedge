# CURSOR CORRECTION t5168u — market96 MARKET absolute-error schema

Date: 2026-11-02 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER **8e571382** · Cos ORDER **ca4dac65**.
Same draft **#701**. HARD END 02:30 EST / 07:30Z.

**No new scientific look.** Additive market96 MARKET absolute-error schema
correction on frozen JOINED_ROWS. Does not invoke the one-exec runner,
`--score`, or `--cos-bind`. Does not claim / reset / rebind. Does not
regenerate forecasts. Does not rewrite accepted EXEC or t5165u addendum
scientific bytes. Alex **ebddd100** / Cos **7548b001** stand — no full
re-review. Q2 is diagnostic only, not a market substitute. Three arms =
candidate / IF / **MARKET**.

## Immutable EXEC (cited, not rewritten)

| Item | Value |
| --- | --- |
| Tip | `093a51dc9d6ef4c18fb16101a02c7395ce074096` |
| Stamp | `3001dcc32f4425596727a3c0ebb4a052bc1bd37f` |
| bind_id | `4eef5d1f843bb17327d0d81d3cdae3a8d7d91917d9763691b55808c365d0caa6` **CONSUMED** |
| ONE_RUN.json | `9a72c55be94e0fc04778da22748a70b2e159c4c95e4803c41449cbb8abfc13cc` |
| RECEIPT.json | `f8da3deab88858405fc55c0af829fde53ef4a689b697cd7a773442e564355869` |

## Immutable addendum (cited, not rewritten)

| Item | Value |
| --- | --- |
| Tip | `fa60e4b6f58669f9c8b914d9945c53e0c9d5bb2c` |
| Stamp | `e317fc05b9f79dd3bee2183dd5622656594aefab` |
| JOINED_ROWS.json | `df24500e4366240ca6aa7d1aedab0c8415a8bea17dbfe969d6e9fac96e77a5a0` |
| REPORTING_ADDENDUM.json | `64516e39ac908d75a85ad11e305ad0100afd8e55238750b5c1fd724bb9aaf96c` |

same96 filter only. market∩96 `072e99e0` / `558fbfe5`.

## Schema (overall + per-season)

Absolute MAE/RMSE/bias for candidate, IF, and **MARKET**. Q2 cited as
diagnostic only. Paired IF−market / candidate−market cited from EXEC
RECEIPT (not recomputed).

| Split | n | mae_market | rmse_market | bias_market |
| --- | ---: | ---: | ---: | ---: |
| overall | 96 | 10.044270833333334 | 12.854023162354009 | −1.4140625 |
| 2020 | 41 | 10.945121951219512 | 13.703357697846245 | +0.5304878048780488 |
| 2021 | 55 | 9.372727272727273 | 12.18242027005979 | −2.8636363636363638 |

Owner citation match: exact float equality. Cited IF/Q2/candidate abs
from frozen addendum (not a new look): mae_if 11.194598 / mae_q2
diagnostic 10.654382 / mae_candidate 10.663846. IF−market 1.150327
cited EXEC; candidate−market 0.619575 cited EXEC.

Guards: missing/nonfinite market errors → fail; wrong market cohort
(n≠96 or seasons ≠41/55) → fail.

## Correction hashes

| Hash | sha256 |
| --- | --- |
| code | `32252c5384f91bb5a96c51e1f29438539259b6638029c6b8d866dddb2afbce52` |
| input | `48e99cd608c7099a18d8beb3008ebd99b87f5f3ae1b9bb1949c9bf6ac51d8d0e` |
| output | `5224f79f47d584ef5872a77fea85deae35048fd01b586df7de889bb334110be0` |
| MARKET96_SCHEMA_CORRECTION.json | `38f78d3311c9066a117932672765e1e35a24868be2c17d1d99028c74cded7b42` |

Command: `PYTHONPATH=services/model-service python scripts/nfl/run_nfl_t5168u_market96_schema_correction.py`

Focused tests: `services/model-service/tests/test_nfl_t5168u_market96_schema.py` — 6 passed.
Not added to FOCUSED_TESTS (EXEC-adjacent verify hash stands).

**STOP for Cos ACCEPT → Alex delta-check (columns/guards only).** CERT=0. No merge.
