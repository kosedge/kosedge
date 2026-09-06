# Semantic parity matrix — PR #491 → clean PR A/B (Phase 2.6F / d05b)

Source (reference only, untouched): PR #491 @ `2d51cdcdc0d0d87c185352388f1ea891992b24f3`

| #491 capability / artifact                                | Destination                       | Parity                 |
| --------------------------------------------------------- | --------------------------------- | ---------------------- |
| Holdout package modules (`holdout_2425/*`)                | PR A (#498)                       | FULL                   |
| Identity expansions (`ncaam_identity.py`, `aliases.json`) | PR A                              | FULL                   |
| Evaluator seal gate                                       | PR A                              | FULL                   |
| Venue / schedule normalize / KenPom+odds audit code       | PR A                              | FULL                   |
| Foundation + phase26c unit tests                          | PR A                              | FULL                   |
| Scripts (`build_*`, `run_2425_*`, ingest)                 | PR A                              | FULL                   |
| Web-python allowlist                                      | PR A                              | FULL                   |
| ADR / offline Mac runbook / split plan docs               | PR A (ADR ACCEPTED)               | FULL+                  |
| Tiny ESPN fixture                                         | PR A (synthetic)                  | REPLACED (no raw days) |
| Coverage 26b/26c **summaries** & small audits             | PR B                              | FULL                   |
| Seal receipts + quarantine summaries                      | PR B                              | FULL                   |
| Feature/label **manifests** (hashes only)                 | PR B                              | FULL                   |
| Readiness report                                          | PR B                              | FULL                   |
| R2 object refs + sanitized storage receipts               | PR B (new)                        | ADDED                  |
| Retention documentation (prefix + bucket-wide)            | PR B (new)                        | ADDED                  |
| `rejected_events.json` row dump                           | Deferred (hash in seal)           | HASH_ONLY              |
| `schedule_sot_index.json`                                 | Deferred (hash recorded)          | HASH_ONLY              |
| `reversal_orientation_full.json`                          | Deferred (hash recorded)          | HASH_ONLY              |
| Offline recovery gap lists                                | Deferred (hash recorded)          | HASH_ONLY              |
| Raw ESPN scoreboard archive (156 JSON + 156 sha256)       | R2 `espn_schedule_raw_v1/`        | EXTERNAL               |
| `features.json` / `labels.json` bulk                      | Deferred / not git                | EXTERNAL               |
| Large row dumps (venue/odds/kenpom/ledger)                | Deferred / not git                | EXTERNAL               |
| `ncaam_official_schedule_2024_25.json` bulk pack          | Deferred / not git                | EXTERNAL               |
| Credentials / uploader tokens                             | Revoked; absent from git          | CLEAN                  |
| Scoring / unseal / Test-A / B2-PACE                       | Not implemented                   | N/A (hard stop)        |
| PR #491 branch/history rewrite                            | Untouched                         | PRESERVED              |

## Counts

| Metric              | PR #491              | PR A (#498)     | PR B (stacked)           |
| ------------------- | -------------------- | --------------- | ------------------------ |
| Intent              | monolithic code+bulk | code foundation | manifests + R2 refs      |
| Bulk ESPN in git    | yes (~100 MiB)       | no              | no                       |
| Large row dumps     | yes                  | no              | no (hashes only)         |
| Seal remains sealed | yes                  | yes             | yes                      |

## Useful #491 contracts preserved

- `holdout_id`: `ncaam_holdout_2024_25_v1_1`
- Feature/label content + manifest sha256 values unchanged (see `seal/seal_receipt.json` + `r2_object_refs`)
- `rejected_sha256` preserved without embedding the row dump
- Evaluator refuses evaluation by default (`evaluator_gate`)
- Phase 2.6C threshold lock + seal governance summaries retained
