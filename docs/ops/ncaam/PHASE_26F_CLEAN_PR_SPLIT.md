# Phase 2.6F — clean PR A/B split (execution)

**Status:** IN PROGRESS (PR split open; storage portion verified externally)  
**Supersedes plan-only:** `PR491_SPLIT_MIGRATION_PLAN_26C.md` (plan retained for history)  
**Does not close:** PR #491 (remains draft until Ryan reviews A/B + parity)

## PR A — Code foundation

Branch: `cursor/ncaam-holdout-foundation-16f9`

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

Branch: `cursor/ncaam-holdout-governance-16f9` (stacked on A)

Includes:

- R2 object references + exact prefixes + content/manifest hashes
- Sanitized provider-verification receipts (no credentials)
- Seal / coverage / integrity / quarantine summaries
- Retention documentation (prefix + bucket-wide)

Excludes:

- Raw payloads / bulk binary data
- Secrets / API tokens / S3 credentials

## Storage verdict (Phase 2.6F storage portion — complete)

| Gate                         | Status            |
| ---------------------------- | ----------------- |
| R2 upload                    | GREEN             |
| Fresh-download verification  | GREEN             |
| Retention controls           | PROVIDER_VERIFIED |
| Temporary credential revoked | GREEN             |
| Holdout seal                 | REMAINS SEALED    |

Exact prefixes/hashes: `data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/` on PR B.

## Hard stops (this phase)

- No scoring / unseal
- No B2-PACE-NEUTRAL-v1
- No merge / deploy / model change
- No rewrite / close / force-push of PR #491
