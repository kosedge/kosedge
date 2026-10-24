# O-1..O-7 contract (`b7364186`)

Quoted defects, implemented in `run_injury_holdout_opening.py`.

## O-1 (blocker)

One process: lock check → lock write → holdout export write by frozen Path 1
writer → D-2 guards (`.v2` pin, TZ census, incomplete rule) → close/outcome
join → score (import `ca98ae0e` by sha-verified path). No tuning/refit.
Fail closed after the lock is consumed.

This package **does not** execute the real opening. `--mode holdout` without
`--workspace` STOPs before any lock. With `--workspace` under `fixtures/`,
the sequence runs; 2024/25 listings are absent, so export STOPs after the
fixture lock is consumed. No 2024/25 byte is read.

## O-2

Pins asserted **before** lock write: fit `6a5490db`, frozen export `d87e6129`,
writer `9947b880`, frozen script `8d188da2`, null contract `ff8e6527`.

## O-3

- existing lock → STOP
- lock written 0444 with sha, only under `fixtures/`, before any 2024/25 read
- second invocation → STOP
- abort after lock records `consumed`
- production path `/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock` is never written

## O-4

`F-HOLDOUT` is `main(["--mode","holdout","--workspace", fixture])`, not a
bare `die()`. Also: lock-present, double-open, refit-attempt, and
`main(["--mode","holdout"])` default (blocked, no lock).

## O-5

Complete rows require non-null `source_ts_home` and `source_ts_away`.

## O-6

`out/runner.log` captures stderr STOP lines and is in SHA256SUMS.

## O-7

`notes/o7-d2-expected-answers-commit-order.md`: `ff3b3b0b` 15:05:39Z before
D-2 runner `62c6f8d6` 15:07:24Z. Still secondhand for IMV (no git).
