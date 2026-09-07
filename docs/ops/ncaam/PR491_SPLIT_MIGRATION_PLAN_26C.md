# PR491 split migration plan (Phase 2.6C)

**Status:** SUPERSEDED by execution — see `PHASE_26F_CLEAN_PR_SPLIT.md`.  
PR #491 remains draft/unchanged until Ryan reviews clean PR A/B.

## Goal

Split the holdout raw/ingestion landing into three independently reviewable tracks so
code+tests can ship without embedding ~100 MiB of raw ESPN JSON in git history.

## Track 1 — reusable ingestion code / schema / tests

- ESPN ingest + B7 map helpers
- Schedule SoT schema / normalize
- Foundation + Phase 2.6C pytest
- **Exclude:** bulk `espn_scoreboard_*.json`

## Track 2 — manifests + small fixtures

- Day receipts / sha256 manifests
- Tiny CI fixtures (1–3 days)
- Audit summaries (no outcome joins)

## Track 3 — externally stored immutable raw dataset

- Object-store prefix for full-window raw + sidecars
- Fetch/verify script gated on Ryan-approved URI
- **Blocked until** storage ADR decision
- **Never** delete local raw before remote verify

## Hard stops

No migration execution in 2.6C. No raw deletion. Await Ryan.
