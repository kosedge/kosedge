# Semantic parity matrix — PR #491 → clean PR A/B (Phase 2.6F CR4)

| #491 capability / artifact                                | Destination            | Classification                                              | Parity                           |
| --------------------------------------------------------- | ---------------------- | ----------------------------------------------------------- | -------------------------------- |
| Holdout package modules (`holdout_2425/*`)                | PR A                   | reproducible (git)                                          | FULL+ (CR4 R2 recovery)          |
| Identity expansions (`ncaam_identity.py`, `aliases.json`) | PR A                   | reproducible (git)                                          | FULL+ (governed mascot strip)    |
| Evaluator seal gate                                       | PR A                   | reproducible (git)                                          | FULL                             |
| Venue / schedule / KenPom+odds audit code                 | PR A                   | reproducible (git)                                          | FULL+ (B1/PIT fail-closed)       |
| Foundation + phase26c + CR4 unit tests                    | PR A                   | reproducible (git)                                          | FULL+ (CR3+CR4 mock R2)          |
| Scripts (`build_*`, `hydrate_*`, `recover_*`, `verify_*`) | PR A                   | reproducible (git)                                          | FULL+ (path B CR4 R2)            |
| Forensic raw+KenPom+odds script                           | PR A                   | forensic only (cannot promote frozen)                       | ADDED                            |
| Web-python allowlist                                      | PR A                   | reproducible (git)                                          | FULL                             |
| ADR / offline Mac / split / rebuild / CR4 DR docs         | PR A                   | reproducible (git)                                          | FULL+ (R2 authority)             |
| B1 drift forensic note                                    | PR A                   | docs only (Alex ownership; no B1 code)                      | ADDED                            |
| Tiny ESPN fixture                                         | PR A (synthetic)       | reproducible (git)                                          | REPLACED (no raw days)           |
| Coverage 26b/26c summaries & audits (small)               | PR B                   | hash-only / summary manifests                               | FULL                             |
| Seal receipts + quarantine + schedule_sot manifests       | PR B                   | hash-only (bytes R2-hydrated)                               | FULL (`seal_payload_sha256`)     |
| Feature/label **manifests** (hashes only)                 | PR B                   | hash-only                                                   | FULL                             |
| Readiness report                                          | PR B                   | hash-only + storage overlay                                 | FULL+                            |
| R2 object refs + dual-bucket CR4 contract                 | PR B                   | R2-backed refs (CoS upload PENDING)                         | UPDATED                          |
| Retention documentation                                   | PR B                   | reproducible (git)                                          | UPDATED (features + label vault) |
| Raw ESPN scoreboard archive (312 files)                   | legacy gap-recovery R2 | **R2-backed forensic**                                      | EXTERNAL→R2 (not authority)      |
| `features.json` bulk                                      | features bucket        | **R2 exact frozen bytes** (`8c9e7fff…`)                     | recovery locked (CR4)            |
| `labels.json` bulk                                        | label vault bucket     | **R2 exact frozen bytes** (`aa7e1088…`); builders forbidden | recovery locked (CR4)            |
| Large row dumps (venue/odds/kenpom/ledger/recovery)       | deferred / not git     | **hash-only** (rebuildable summaries in git)                | deferred                         |
| Stripped oversized ops JSON (rejected/schedule/etc.)      | features R2 / deferred | **R2 exact / hash-only**                                    | CR4 inventory                    |
| `ncaam_official_schedule_2024_25.json` bulk pack          | features bucket        | **R2 exact frozen bytes** (`4016f2ab…`)                     | recovery locked (CR4)            |
| Credentials / uploader tokens                             | Absent from git        | CLEAN                                                       | CLEAN                            |
| Scoring / unseal / B2-PACE-NEUTRAL-v1                     | Not implemented        | N/A                                                         | hard stop                        |
| PR #491 / #490 / #496 / #497                              | Untouched              | PRESERVED                                                   | PRESERVED                        |
| Fat JSON ancestor `7ced9f10`                              | Not in A/B history     | CLEAN                                                       | CLEAN                            |

## Classification legend

- **R2-backed / R2 exact frozen bytes**: authoritative disaster recovery hydrates exact CAS objects from private retention-locked buckets; git holds refs/inventory only. CoS provisions upload.
- **reproducible**: rebuildable from git code + documented inputs.
- **path-B CR4**: hydrate → staging → verify inventory+locked hashes → reseal (frozen v1.1 identity) → atomic promote; live seal never unlinked first; builders cannot access label vault; no Odds API fallback.
- **forensic only**: raw+KenPom+odds reconstruction for investigation; must not redefine or promote frozen holdout.
- **hash-only**: content deferred; git holds digests/manifests (not false EXTERNAL).

## Counts

| Metric                          | PR #491              | PR A                  | PR B (stacked)                |
| ------------------------------- | -------------------- | --------------------- | ----------------------------- |
| Intent                          | monolithic code+bulk | fixed code foundation | manifests + CR4 R2 refs       |
| Bulk ESPN in git                | yes (~100 MiB)       | no                    | no                            |
| Fat ops JSON in merge ancestors | yes (old B)          | no                    | no                            |
| Seal remains sealed             | yes                  | yes                   | yes                           |
| Clean-checkout seal recovery    | N/A                  | path B CR4 (mock R2)  | inherits A + dual-bucket refs |
