# ADR 2026-09-05 — NCAAM holdout raw object storage

**Status:** ACCEPTED (executed in Phase 2.6F storage portion; PR split follows)  
**Phase:** 2.6C plan → 2.6F storage verified → clean PR A/B split

## Context

Raw ESPN scoreboard payloads for the 2024–25 sealed holdout previously lived under
`data/ops/lab/ncaam/holdout_2024_25/raw/espn_scoreboard/` (~100 MiB, 156 day pairs).
Landing them as a single PR #491 git blob is blocked for enterprise hygiene.

NFL already has an optional remote dump pattern (`NFL_DR_REMOTE_URI` + sha256 sidecars).

## Decision

**A_s3_r2_immutable_prefix** — private Cloudflare R2 bucket with day/object-keyed
immutable objects + sha256 / inventory sidecars. Git holds code + small manifests +
object references only.

Bucket: `kosedge-ncaam-lab-gap-recovery-raw-v1` (private; public access disabled).

Primary prefixes (see PR B `r2_object_refs`):

- `ncaam/gap_recovery_research_subset_v1/`
- `ncaam/holdout_2024_25/espn_schedule_raw_v1/`

## Retention (document; do not change mid-phase)

Provider-verified as of Phase 2.6F storage close:

1. **Prefix-specific lock rules** (narrower):
   - `retain-gap-recovery-research-subset-v1` → prefix `ncaam/gap_recovery_research_subset_v1/` → retention `indefinite`
   - `retain-holdout-2024-25-espn-schedule-raw-v1` → prefix `ncaam/holdout_2024_25/espn_schedule_raw_v1/` → retention `indefinite`

2. **Bucket-wide indefinite rule** (broader impact than the two prefix rules):
   - Applies to the entire bucket, not only holdout prefixes.
   - **Documented intent for Phase 2.6F:** treat as **intentionally permanent** for sealed lab immutability while this holdout remains sealed.
   - **Do not modify/remove mid-phase.** Any future narrowing (prefix-only locks, timed retention) requires a separate Ryan-approved change after PR A/B review.
   - Rationale for permanence: prevents silent overwrite/delete of sealed research objects; broader blast radius is accepted until a follow-on retention policy review.

## Non-goals (this ADR close-out)

- No holdout unseal / scoring
- No PR #491 rewrite/close in this phase
- No mid-phase retention edits

## Consequences

- `BLOCKED_STORAGE_ARCHITECTURE` from Phase 2.6C is resolved by R2 + receipts.
- Timestamp integrity / coverage review blockers may remain on the sealed package.
- Clean PR A/B replace the bulk-in-git approach; #491 stays draft until Ryan reviews.
