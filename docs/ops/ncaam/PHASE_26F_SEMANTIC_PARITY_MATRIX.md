# Semantic parity matrix — PR #491 → clean PR A'/B' (Phase 2.6F acceptance fix)

| #491 capability / artifact | Destination | Classification | Parity |
| --- | --- | --- | --- |
| Holdout package modules (`holdout_2425/*`) | PR A' | reproducible (git) | FULL |
| Identity expansions (`ncaam_identity.py`, `aliases.json`) | PR A' | reproducible (git) | FULL+ (governed mascot strip) |
| Evaluator seal gate | PR A' | reproducible (git) | FULL |
| Venue / schedule / KenPom+odds audit code | PR A' | reproducible (git) | FULL+ (B1/PIT fail-closed) |
| Foundation + phase26c unit tests | PR A' | reproducible (git) | FULL+ |
| Scripts (`build_*`, `hydrate_*`, `verify_*`, `run_2425_*`) | PR A' | reproducible (git) | FULL+ |
| Web-python allowlist | PR A' | reproducible (git) | FULL |
| ADR / offline Mac runbook / split / rebuild docs | PR A' | reproducible (git) | FULL+ |
| Tiny ESPN fixture | PR A' (synthetic) | reproducible (git) | REPLACED (no raw days) |
| Coverage 26b/26c summaries & audits (small) | PR B' | hash-only / summary manifests | FULL |
| Seal receipts + quarantine + schedule_sot manifests | PR B' | hash-only | FULL (`seal_payload_sha256`) |
| Feature/label **manifests** (hashes only) | PR B' | hash-only | FULL |
| Readiness report | PR B' | hash-only + storage overlay | FULL+ |
| R2 object refs + sanitized storage receipts | PR B' | R2-backed refs | ADDED |
| Retention documentation | PR B' | reproducible (git) | ADDED |
| Raw ESPN scoreboard archive (312 files) | R2 `espn_schedule_raw_v1/` | **R2-backed** | EXTERNAL→R2 |
| `features.json` / `labels.json` bulk | deferred / not git | **hash-only** (content sha in manifests) | deferred |
| Large row dumps (venue/odds/kenpom/ledger/recovery) | deferred / not git | **hash-only** | deferred |
| Stripped oversized ops JSON (rejected/schedule/etc.) | deferred / not git | **hash-only** (manifests in git) | deferred |
| `ncaam_official_schedule_2024_25.json` bulk pack | deferred / not git | **hash-only** | deferred |
| Credentials / uploader tokens | Revoked; absent from git | CLEAN | CLEAN |
| Scoring / unseal / B2-PACE-NEUTRAL-v1 | Not implemented | N/A | hard stop |
| PR #491 / #490 | Untouched | PRESERVED | PRESERVED |
| Fat JSON ancestor `7ced9f10` | Not in A'/B' history | CLEAN | CLEAN |

## Classification legend

- **R2-backed**: bytes live in locked R2 prefixes; git holds refs only.
- **reproducible**: rebuildable from git code + documented inputs.
- **hash-only**: content deferred; git holds digests/manifests (not false EXTERNAL).

## Counts

| Metric | PR #491 | PR A' | PR B' (stacked) |
| --- | --- | --- | --- |
| Intent | monolithic code+bulk | fixed code foundation | manifests + R2 refs |
| Bulk ESPN in git | yes (~100 MiB) | no | no |
| Fat ops JSON in merge ancestors | yes (old B) | no | no |
| Seal remains sealed | yes | yes | yes |
