# R-1..R-9 contract (`a8958e85`) — expected before the runner

Quoted defects. Implemented in the v2 runner after this filing.

## R-1

`write_holdout_export_path1` must invoke writer `9947b880` (import/exec +
`timestamps_for_game` + `write_sidecar_chain`). The holdout export can be
produced on a fixture workspace.

## R-2

After lock: pin `.v2`, TZ census, incomplete rule, join, score, receipt.
Lock-gated holdout-season allowance (2024/25 only, after the lock) in runner
guards. Tests never read a 2024/25 byte. 2026 stays forbidden.

## R-3

Record/HFA method per request v3.1 §2. No hardcoded `-3.0` / `45.0`.
`residual_complete` from complete + non-null deltas.

## R-4

Production lock path `/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock`
exists in code. Enabled only when an IMV opening-runner PASS sha is present
and verified. Not a flag or env. Absent this package → STOP, no write.

## R-5

Lock stays 0444. Consumption in `holdout-once.lock.consumed` (0444, reason,
utc, lock sha).

## R-6

Lock carries every EXACT PINS field in `t_expected/HOLDOUT_EXPECTED.json`
`lock_fields`.

## R-7

Receipt writer emits every `receipt_schema` field.

## R-8

`F-E2E`: synthetic lock → export → guards → join → score → receipt.
Fixture season 2022 only.

## R-9

Copy fixtures to a temp dir. Do not unlink in-package locks.
Exclude `__pycache__` from `seeded/`.
