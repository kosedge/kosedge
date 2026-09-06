# Phase 2.6F — clean PR A/B split (execution)

**Status:** IN PROGRESS (PR split open; storage portion verified externally)  
**Supersedes plan-only:** `PR491_SPLIT_MIGRATION_PLAN_26C.md` (plan retained for history)  
**Does not close:** PR #491 (remains draft until Ryan reviews A/B + parity)

Source/reference only: PR #491 (`cursor/ncaam-2425-sealed-holdout-73d9` @ `2d51cdcdc0d0d87c185352388f1ea891992b24f3`) — not rewritten, closed, force-pushed, or deleted.

## PR A — Code foundation

Branch: `cursor/ncaam-holdout-foundation-d05b`

Includes:

- Reusable holdout ingestion / normalize / venue / identity / seal / evaluator gate
- Schemas + contracts + Phase 2.6C thresholds
- Foundation + phase26c unit tests
- Ops docs + allowlist
- Tiny synthetic fixtures only

Excludes:

- Raw ESPN archive
- Model-ready bulk datasets (`features.json`, `labels.json`, large row dumps)
- Generated binary packages
- Credentials

## PR B — Manifests and sealed metadata

Branch: `cursor/ncaam-holdout-governance-d05b` (stacked on A)

Includes:

- R2 object references + exact prefixes + content/manifest hashes
- Sanitized provider-verification receipts (no credentials)
- Seal / coverage / integrity / quarantine **summaries** (no large row dumps)
- Retention documentation (prefix + bucket-wide)

Excludes:

- Raw payloads / bulk binary data
- Large row dumps (`rejected_events.json`, `schedule_sot_index.json`,
  `reversal_orientation_full.json`, offline recovery gap lists, venue/odds/kenpom rows)
- Secrets / API tokens / S3 credentials

## Storage verdict (Phase 2.6F storage portion — complete; do not redo)

| Gate                         | Status            |
| ---------------------------- | ----------------- |
| R2 upload                    | GREEN             |
| Fresh-download verification  | GREEN             |
| Retention controls           | PROVIDER_VERIFIED |
| Temporary credential revoked | GREEN             |
| Holdout seal                 | REMAINS SEALED    |

Bucket: `kosedge-ncaam-lab-gap-recovery-raw-v1`  
Prefix: `ncaam/holdout_2024_25/espn_schedule_raw_v1/` (156 JSON + sha256 sidecars)  
Prefix locks: `retain-gap-recovery-research-subset-v1`, `retain-holdout-2024-25-espn-schedule-raw-v1`  
Bucket-wide: `ncaam-recovery-archival-indefinite` intact  

Exact prefixes/hashes: `data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/` on PR B.

## Hard stops (this phase)

- No scoring / unseal / Test-A
- No B2-PACE / B2-PACE-NEUTRAL-v1 promote
- No Odds API spend / board / PLAY
- No scorecard / gate / B1 changes
- No merge / deploy / model change
- No rewrite / close / force-push of PR #491
