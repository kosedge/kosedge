# Offline Mac recovery runbook — TIMESTAMP_DISHONEST (Phase 2.6C)

## Purpose

Recover honest open/close snapshot times for odds events currently marked
`TIMESTAMP_DISHONEST` (expected n=2006) from Ryan's offline Mac historical archive.

## Acceptance rule (unchanged)

`source_snapshot_time < event_tip`

Do **not** relabel post-tip snapshots as honest. Do **not** invent closes.

## Cloud / agent hard stops

- Do **not** mount or access the external drive from cloud agents
- Do **not** spend Odds API credits to backfill
- Do **not** apply recovery in Phase 2.6C (`recovery_applied=false`)

## Offline operator steps (Ryan Mac only)

1. Load `coverage_26c/offline_mac_recovery_manifest.json` rows.
2. For each `odds_event_id`, locate archive quotes whose capture time is strictly before tip.
3. Prefer book-consistent open/close pairs; retain provider event id.
4. Emit a recovery receipt (sha256 of source files + accepted timestamps).
5. Hand receipt to a future phase for rematerialize — not 2.6C.

## Out of scope

Scoring, ATS/ROI/CLV, unseal, model evaluation.
