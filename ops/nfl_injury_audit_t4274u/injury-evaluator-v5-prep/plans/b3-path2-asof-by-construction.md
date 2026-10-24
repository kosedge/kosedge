# B-3 Path 2 — as-of by construction (NOT CHOSEN)

Ruling `88da5f42` acceptable alternative. Ryan chose Path 1 (`1298bddb`).
This file is the unexecuted plan required by the v5-prep instruction.

## Code-read part (already satisfied in form)

Frozen `8d188da2` `last_report_before_kickoff` L317-340:

- keep only listings with parsed `date_modified` < kickoff (strict)
- unparseable or late rows counted as `n_asof_fail` and dropped
- no usable listing → `units_null` (NULL, not healthy 0)

Helpers (8e2a15ac `nfl_injury_null_contract.py`):

- `parse_fit_kickoff_utc` — naive nflverse gameday/gametime are `America/New_York`; never 23:59:59
- `parse_fit_report_time_utc` — naive `date_modified` is treated as UTC (unlike the evaluator leak check, which must treat naive as ET)

## Still required if Path 2 were chosen (do not execute)

(a) Deposit the text of those two helpers with path, sha, line cites.
(b) Per-row deposit for all 2863 le2023 games produced by the frozen helpers, not new logic:
    game_id, kickoff_utc (= fit_ledger), per-side listing_as_of / max usable date_modified,
    n_usable, n_asof_fail. 0 violations of source_ts ≤ as_of_ts < kickoff.
(c) Evaluator ingests that deposit, sha-pinned, joined by game_id; dies on missing date or game_id mismatch.

Disclosed limitation (would be stated in the request): `date_modified` is a record-modification
time, not a publication time. Late modification is excluded (conservative); backdating is undetectable.

## Status

UNEXECUTED. Path 1 is the authorized path.
