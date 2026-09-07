# Phase 2.6F — clean PR A/B split (execution)

**Status:** ACCEPTANCE FIX IN PROGRESS — CR4 Path B authoritative R2 disaster recovery (A/B); do not merge; #490/#491/#496/#497 untouched
**Supersedes plan-only:** `PR491_SPLIT_MIGRATION_PLAN_26C.md` (plan retained for history)  
**Does not close:** PR #491 (remains draft until Ryan reviews A/B + parity)  
**Prior drafts:** #496 / #497 failed acceptance — replaced by clean A'/B' branches from current `deploy-vercel` (no fat JSON ancestor `7ced9f10` in merge history).

## PR A — Code foundation (CR4 on CR3)

Branch: `cursor/ncaam-26f-foundation-fix-8a49`

Includes prior CR3 plus CR4:

- **Authoritative Path B recovery** = private R2 hydrate of exact frozen v1.1 packages (not regenerate from raw+KenPom+odds)
- Features-bucket hydrate vs **separate label-vault** hydrate (builders fail closed)
- Staging → verify inventory+locked hashes → reseal (frozen identity) → release-pointer promote (`CURRENT` symlink); live seal never unlinked first
- Credential-free recovery receipt; forensic raw+KenPom+odds script cannot promote frozen holdout
- CR4 tests (mock R2): dual recovery identity, locked hashes, fail-closed missing/corrupt/restricted, interrupt/promote preserve, builders blocked, no Odds API fallback

Includes:

- Reusable holdout ingestion / normalize / venue / identity / seal / evaluator gate
- **Identity fail-closed:** governed mascot/campus-locator strip only (no generic strip-final-token)
- **B1 fail-closed:** parseable tip+open+close with strict open < tip and close < tip
- **Raw integrity:** every JSON requires verified sha256 sidecar (no `or True`)
- **Seal hash semantics:** `seal_payload_sha256` + external file digest
- **KenPom PIT:** locked filename-as-of policy; both bridged teams + AdjEM/AdjT required
- Schemas + contracts + Phase 2.6C thresholds (taxonomy relabel)
- Foundation + phase26c unit tests
- Rebuild/hydrate/verify/recover scripts + seal semantics + CR4 R2 DR docs
- **Path B recovery (CR4/CR5):** R2 hydrate of exact frozen packages → staging → verify → reseal → release-pointer promote (builders cannot access label vault)
- **Forensic only:** raw+KenPom+odds rebuild script cannot redefine/promote frozen holdout
- **Raw fail-closed on build path:** missing/mismatched sidecars refuse sealing
- Ops docs + allowlist
- Tiny synthetic fixtures only
- B1 drift forensic note (Alex ownership; no B1 code changes)

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

## Storage verdict (Phase 2.6F CR4 — dual private buckets)

| Gate                         | Status                                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------------- |
| Features bucket contract     | DOCUMENTED (`…-features-v1`) — CoS UPLOADED verified                                               |
| Label vault contract         | DOCUMENTED (`…-label-vault-v1`) — CoS UPLOADED verified                                            |
| Public / r2.dev / custom dom | disabled / none (contract)                                                                         |
| Retention locks              | indefinite (CoS); `provider_verified` on sanitized provider receipt — **not** on inventory objects |
| Inventory SoT                | `_load_inventory` / `default_package_inventory`: 10/10 UPLOADED + non-null CAS keys                |
| Builder label-vault creds    | FORBIDDEN                                                                                          |
| Temporary credential in git  | ABSENT                                                                                             |
| Holdout seal                 | REMAINS SEALED                                                                                     |
| Legacy gap-recovery raw      | retained for forensic ESPN hydrate only                                                            |

Exact prefixes/hashes: `data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/` on PR B (CoS fills CAS keys post-upload).

## Hard stops (this phase)

- No scoring / unseal
- No B2-PACE-NEUTRAL-v1
- No merge / deploy / model change
- No rewrite / close / force-push of PR #491
- No touch of PR #490 / #496 / #497
- No cloud-agent real R2 upload / no secrets in git
- No Odds API / live-data fallback for holdout recovery
- Forensic rebuild must not promote frozen holdout
- No B1 code changes (forensic note only)
