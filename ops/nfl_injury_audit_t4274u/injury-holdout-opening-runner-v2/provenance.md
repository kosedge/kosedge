# Provenance — holdout opening runner v2 (not opened)

No secrets. Paths are package-relative.
- IMV RETURN `a8958e850cd75cce5a24feda95a865e86ca39a2afaff5144748f70cfe4dcbeaa`
- Ryan CLEAR `t4335s14919` / `fabf87320453c274b2b8ec8e443b8af4709d8d24ff8fb6baa449fe3d739d4bd0`
- IMV D-2 ruling `b7364186cc2aa900fd39e2dd22e78e2e69b63d2cac11fd6fa6b234997494b6b8`
- Request v3.1 `35cbb56e10cfe0ec3730441a453f171bda917e7c58ad3e5eb2fe2c573de5ef7b`
- Scorer `ca98ae0e70fcdee77d46aed3c4f9be5644079da6adf08411891e1d5b7970e6c6`
- Writer `9947b880bc789192a26b850ee53dc89d4c43a4c107bdf3fc549c65730739d58f`
- Fit `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657`
- Frozen export `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8`
- Frozen script `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c`
- Null contract `ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2`
- Record baseline CSV `502110cfc9293d96fd5635fbfdd3fad2c19367fa043ce3770cfbae05f2cdbe12`
- Baseline method `record_hfa_baseline_method.py` sha `d8cc9b70f969254b6d88cc35a90c10d258cdc3723def71ac15968faeceb6a2d1`
- Expected answers file `cda0da90a18db4872a784f3ae245d5047e05eb03af0579749e5a1bcef248e441`
- Expected answers commit `73b537b2e394def333e2ad5ce22a24ecc42d9ff2` (before runner `e73c05b6`)
- Seed 20261023. Sigma 13.5 / 14.0.
- NFL_TOTALS_*: unset. Real lock: not written. Tokens: none.
- 2024/25: not opened.

## R self-check (file:line vs this package)

All lines are `run_injury_holdout_opening.py` unless noted.

### R-1 export invokes writer 9947b880

- `400` `def import_writer()` — sha-verifies `9947b880`, execs the module
- `416` `def write_holdout_export_path1`
- `418` `writer = import_writer()`
- `438` `ts = writer.timestamps_for_game(game, complete)`
- `461` `writer.write_sidecar_chain(...)`
- F-E2E receipt `writer_invoked: true`

### R-2 post-lock sequence + lock-gated 2024/25 allowance

- `779` `def run_holdout_workspace` — lock → export → `.v2` pin → TZ → incomplete → join → score → receipt
- `160` `def holdout_season_allowed` — 2024/25 only after `lock_written`; 2026 never
- `170` `def may_open_holdout_listings` — open `listings_2024/2025` only after production lock + verified PASS sha
- Tests never create or read a 2024/25 file. E2E seasons = `[2022]`.

### R-3 record/HFA baseline (not −3.0 / 45.0)

- `record_hfa_baseline_method.py:13` `HFA = 1.05`
- `record_hfa_baseline_method.py:14` `BASE_TOTAL = 45.3`
- `record_hfa_baseline_method.py:38` `team_strength_from_record`
- `record_hfa_baseline_method.py:46` `decompose_record_hfa`
- `record_hfa_baseline_method.py:63` `build_record_book` (prior-week W-L; ties ignore)
- `587` `def join_close`
- `594` `book_base = baseline_method.build_record_book(...)`
- `623` `residual_complete` from complete + non-null deltas (not hardcoded True)
- `634` `baseline_margin` / `baseline_total` from the book
- Week-1 0-0 identity `1.05` / `44.8435` asserted at `807`–`812`
- No `baseline_margin = -3.0` or `baseline_total = 45.0` in this file

### R-4 production lock path, PASS-sha gated

- `36` `REAL_LOCK = Path("/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock")`
- `147` `def verified_opening_pass_sha` — empty `REQUIRED_OPENING_PASS`; not a flag/env
- `304` `def write_lock`
- `309` `die("O-3 lock: production lock requires verified IMV opening-runner PASS sha")`
- `866` `F-PRODUCTION-LOCK-BLOCKED` calls `write_lock(REAL_LOCK.parent, {})`
- Real lock was not written.

### R-5 lock stays 0444; sidecar consumption

- `38` `CONSUMED_NAME = "holdout-once.lock.consumed"`
- `335` `def mark_lock_consumed`
- `336` lock is not chmod'd writable and is not rewritten
- Sidecar fields: `reason`, `utc`, `lock_sha`; mode 0444

### R-6 lock pin set

`lock_payload` `271`–`302` carries: decision+t4335s14919 verbatim, request, readiness+erratum, D-2, opening-runner PASS (null), spec `a156459b`, acceptance `54bc78ec`, runner/scorer/writer, frozen script, null contract, fit, frozen export, le2023 export `a38a55bb`, HEAD `8e2a15ac`, expected sha+commit, baseline-method sha, code tag, utc, operator, `opened once`.

### R-7 receipt writer

- `699` `def write_receipt`
- Emits lock path/mode/sha, export `.v2` sha, TZ counts, n_incomplete+ids by season, n_missing_close by season, F1/F2/pooled n/I-2/I-4/K-4/primary, log sha, MANIFEST/SUMS, stop, `consumed=true`

### R-8 E2E fixture

- `872`–`919` `F-E2E` on a temp copy of `fixtures/e2e` (season 2022 only)
- Covers lock, export (writer), guards, join, score, receipt
- `stop: false`. No 2024/25 bytes.

### R-9 temp-dir fixtures; no seeded `__pycache__`

- `216` `def copy_fixture_to_temp`
- `32` `sys.dont_write_bytecode = True`
- `.gitignore` excludes `__pycache__/` and `*.pyc`
- Checker refuses `seeded/**/__pycache__`

### R-10 (evidence; still secondhand)

Expected-answers commit `73b537b2` (15:27:23Z) before runner commit `e73c05b6`. Git is out of IMV method.

## Institutional memory

`notes/no-prior-grades.md`. No grades invented.
