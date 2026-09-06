# ADR 2026-09-05 — NCAAM holdout raw object storage

**Status:** PROPOSED — awaiting Ryan decision  
**Phase:** 2.6C (inventory + plan only; no provisioning)

## Context

Raw ESPN scoreboard payloads for the 2024–25 sealed holdout live under
`data/ops/lab/ncaam/holdout_2024_25/raw/espn_scoreboard/`
(~99.92 MiB,
156 day files).
Landing them as a single PR491 git blob is blocked.

NFL already has an optional remote dump pattern:

- Env: `NFL_DR_REMOTE_URI=s3://bucket/prefix`
- Tooling: `services/model-service/data_platform_nfl/dr_backup.py` → `upload_dump_if_configured`
- Sidecar: `.sha256` next to the object
- Docs: `docs/NFL_DATA_RESILIENCE.md`

## Decision (pending)

Recommended default (not executed): **A_s3_r2_immutable_prefix** — day-keyed immutable
objects + sha256 sidecars, local cache retained until remote verify succeeds.

## Non-goals (2.6C)

- No bucket provisioning
- No upload / delete of raw
- No PR491 rewrite in this phase
- No scoring / unseal

## Consequences

Until Ryan picks a convention, readiness remains `BLOCKED_STORAGE_ARCHITECTURE`.
