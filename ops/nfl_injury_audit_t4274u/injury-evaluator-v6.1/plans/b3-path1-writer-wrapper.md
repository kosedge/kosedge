# B-3 Path 1 — writer-only wrapper (PREFERRED)

Ruling `88da5f42`. Ryan authorization `1298bddb`:
"Path 1: new export with timestamps; I authorize the pre-2024-only rerun of frozen code"

## What this path does

Re-execute frozen `8e2a15ac` / `8d188da2` on le2023-only inputs with fit object `6a5490db`.
The only change is an export-writer extension, delivered as
`ops/nfl_injury_audit_t4274u/injury-b3-path1-export/write_sealed_injury_export_ts_v1.py`.

Per complete game the wrapper emits:

- `as_of_ts` = max(listing_as_of home, away)
- `source_ts_home` / `source_ts_away` = that side's listing_as_of
- `source_ts` = min of the available per-side listing_as_of (scorer leak field)
- `kickoff_utc`

Incomplete games: all of those timestamp fields are null and are excluded from the leak-pass set.

## What this path must not do

- Edit `d87e6129` / `sealed_injury_export.json`
- Write into `/opt/cursor/artifacts/injury-fit-le2023`
- Touch 2024/25
- Rerun F1/F2/pooled (STOP after this evidence; IMV reviews first)
- Re-search the 729-point Spec C grid (apply frozen selected C + A/B only)

## Evidence required (a–e)

(a) wrapper text + sha + writer-only diff
(b) 2863-row field-wise 0-diff on applied/complete/continuity_*/delta_*/game_id/season/week
(c) recomputed fit_object sha = `6a5490db`; ledger e1/bound/config = C-1
(d) n_null side, n_asof_fail, 0 violations of source_ts ≤ as_of_ts < kickoff
(e) sidecar chain + NOTE citing `09636bec` / `0ad8aca9`

Deposit: `/cursor/stores/self/artifacts/injury-b3-path1-export/` + SHA256SUMS.

## Execution status

Authorized and executed in this cycle. Scorer F1/F2/pooled remain unrun.
