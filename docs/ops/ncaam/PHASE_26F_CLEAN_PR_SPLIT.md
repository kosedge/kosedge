# Phase 2.6F — clean PR A/B split (execution)

**Status:** ACCEPTANCE FIX IN PROGRESS (A'/B' rebuild; do not merge; #491 untouched)  
**Supersedes plan-only:** `PR491_SPLIT_MIGRATION_PLAN_26C.md` (plan retained for history)  
**Does not close:** PR #491 (remains draft until Ryan reviews A/B + parity)  
**Prior drafts:** #496 / #497 failed acceptance — replaced by clean A'/B' branches from current `deploy-vercel` (no fat JSON ancestor `7ced9f10` in merge history).

## PR A' — Code foundation (fixed)

Branch: `cursor/ncaam-26f-foundation-fix-8a49`

Includes:

- Reusable holdout ingestion / normalize / venue / identity / seal / evaluator gate
- **Identity fail-closed:** governed mascot/campus-locator strip only (no generic strip-final-token)
- **B1 fail-closed:** parseable tip+open+close with strict open < tip and close < tip
- **Raw integrity:** every JSON requires verified sha256 sidecar (no `or True`)
- **Seal hash semantics:** `seal_payload_sha256` + external file digest
- **KenPom PIT:** locked filename-as-of policy; both bridged teams + AdjEM/AdjT required
- Schemas + contracts + Phase 2.6C thresholds (taxonomy relabel)
- Foundation + phase26c unit tests
- Rebuild/hydrate/verify scripts + seal semantics doc
- Ops docs + allowlist
- Tiny synthetic fixtures only

Excludes:

- Raw ESPN archive
- Model-ready bulk datasets (`features.json`, `labels.json`, large row dumps)
- Generated binary packages
- Credentials

## PR B' — Manifests and sealed metadata

Branch: `cursor/ncaam-26f-governance-fix-8a49` (stacked on A')

Includes:

- R2 object references + exact prefixes + content/manifest hashes
- Sanitized provider-verification receipts (no credentials)
- Seal / coverage / integrity / quarantine summaries (manifests only — no fat dumps)
- Retention documentation (prefix + bucket-wide)
- HISTORY_AUDIT bound to exact A'/B' HEADs
- Semantic parity matrix with accurate R2 / reproducible / hash-only classifications

Excludes:

- Raw payloads / bulk binary data
- Secrets / API tokens / S3 credentials
- Any ancestor commit containing oversized ops JSON dumps

## Storage verdict (Phase 2.6F storage portion — complete)

| Gate                         | Status            |
| ---------------------------- | ----------------- |
| R2 upload                    | GREEN             |
| Fresh-download verification  | GREEN             |
| Retention controls           | PROVIDER_VERIFIED |
| Temporary credential revoked | GREEN             |
| Holdout seal                 | REMAINS SEALED    |

Exact prefixes/hashes: `data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/` on PR B'.

## Hard stops (this phase)

- No scoring / unseal
- No B2-PACE-NEUTRAL-v1
- No merge / deploy / model change
- No rewrite / close / force-push of PR #491
- No touch of PR #490
