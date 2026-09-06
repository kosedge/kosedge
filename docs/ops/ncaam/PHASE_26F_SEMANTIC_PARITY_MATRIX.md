# Semantic parity matrix — PR #491 → clean PR A/B (Phase 2.6F)

| #491 capability / artifact                                | Destination                       | Parity                 |
| --------------------------------------------------------- | --------------------------------- | ---------------------- |
| Holdout package modules (`holdout_2425/*`)                | PR A                              | FULL                   |
| Identity expansions (`ncaam_identity.py`, `aliases.json`) | PR A                              | FULL                   |
| Evaluator seal gate                                       | PR A                              | FULL                   |
| Venue / schedule normalize / KenPom+odds audit code       | PR A                              | FULL                   |
| Foundation + phase26c unit tests                          | PR A                              | FULL                   |
| Scripts (`build_*`, `run_2425_*`, ingest)                 | PR A                              | FULL                   |
| Web-python allowlist                                      | PR A                              | FULL                   |
| ADR / offline Mac runbook / split plan docs               | PR A (+ ADR updated ACCEPTED)     | FULL+                  |
| Tiny ESPN fixture                                         | PR A (synthetic)                  | REPLACED (no raw days) |
| Coverage 26b/26c summaries & audits (small)               | PR B                              | FULL                   |
| Seal receipts + quarantine + schedule_sot index           | PR B                              | FULL                   |
| Feature/label **manifests** (hashes only)                 | PR B                              | FULL                   |
| Readiness report                                          | PR B (storage overlay annotated)  | FULL+                  |
| R2 object refs + sanitized storage receipts               | PR B (new)                        | ADDED                  |
| Retention documentation (bucket-wide indefinite)          | PR B (new)                        | ADDED                  |
| Raw ESPN scoreboard archive (312 files)                   | R2 prefix `espn_schedule_raw_v1/` | EXTERNAL               |
| `features.json` / `labels.json` bulk                      | Deferred / not git                | EXTERNAL               |
| Large row dumps (venue/odds/kenpom/ledger/recovery)       | Deferred / not git                | EXTERNAL               |
| `ncaam_official_schedule_2024_25.json` bulk pack          | Deferred / not git                | EXTERNAL               |
| Credentials / uploader tokens                             | Revoked; absent from git          | CLEAN                  |
| Scoring / unseal / B2-PACE-NEUTRAL-v1                     | Not implemented                   | N/A (hard stop)        |
| PR #491 branch/history rewrite                            | Untouched                         | PRESERVED              |

## Counts

| Metric              | PR #491              | PR A            | PR B (stacked)      |
| ------------------- | -------------------- | --------------- | ------------------- |
| Intent              | monolithic code+bulk | code foundation | manifests + R2 refs |
| Bulk ESPN in git    | yes (~100 MiB)       | no              | no                  |
| Seal remains sealed | yes                  | yes             | yes                 |

## CoS strip on PR B (#497)

The following oversized ops JSON files were removed from Git and replaced with short hash/summary manifests (not uploaded to R2 in this trim; content hashes retained):

| Removed                                               | Replacement                                                    |
| ----------------------------------------------------- | -------------------------------------------------------------- |
| `rejected/rejected_events.json`                       | `rejected/rejected_events.manifest.json`                       |
| `schedule_sot/schedule_sot_index.json`                | `schedule_sot/schedule_sot_index.manifest.json`                |
| `coverage_26c/reversal_orientation_full.json`         | `coverage_26c/reversal_orientation_full.manifest.json`         |
| `coverage_26c/feature_only_representativeness.json`   | `coverage_26c/feature_only_representativeness.manifest.json`   |
| `kenpom_audit/snapshot_inventory.json`                | `kenpom_audit/snapshot_inventory.manifest.json`                |
| `coverage_26b/offline_archive_recovery_manifest.json` | `coverage_26b/offline_archive_recovery_manifest.manifest.json` |

Receipt: `data/ops/lab/ncaam/holdout_2024_25/r2_object_refs/COS_STRIP_RECEIPT_26F.json`
