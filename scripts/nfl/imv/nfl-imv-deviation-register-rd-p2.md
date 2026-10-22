# Register update — RD-1, RD-2, RD-3, P-2 (e5c65b0d)

Parent: `nfl-imv-deviation-register-t4149u.md` (`39561f48…`). That file is
**frozen**. This addendum only. No Mac run. No parity evidence.

## RD-1 — Sparse missed by R-b

**DEVIATES (process).** Ruling R-b did not require a sparse-checkout
probe. A sparse worktree can hide `services/model-service` or the
canonical schedule pack while porcelain still looks clean. plumb2-3
in runbook v2.4.4 is the check: `core.sparseCheckout` must not be true
and `$BASE/.git/info/sparse-checkout` must be absent or empty. Fail
is STOP.

## RD-2 — Check-7 path erratum

**DEVIATES (process).** Check-7 used a wrong simulator path. The
sealed runner inserts `$BASE/services/model-service` and imports
`src.services.nfl_simulator`. The file is

`$BASE/services/model-service/src/services/nfl_simulator.py`

not `$BASE/src/services/nfl_simulator.py`. plumb2-7 in runbook v2.4.4
tests the `services/model-service/...` path and refuses the erratum
path.

## RD-3 — bash 3.2 + set -u empty array aborted W4

**LOGGED.** Mac `/bin/bash` 3.2.57, `set -u`: `"${PACK_ARG[@]}"` on
an empty array is fatal. The W4 operator run STOPPED in
`nfl-imv-feature-build-v2.4.sh` (expansion at l.254; inside `set +e`,
which does not lift `-u`).

Dir `/var/tmp/nfl-imv-features/w4-20261022T173520Z` is
**ABORTED-PARTIAL**. It is not evidence. Do not edit, delete, seal, or
reuse it. Rerun uses `nfl-imv-feature-build-v2.4.1.sh`
(`${PACK_ARG[@]+"${PACK_ARG[@]}"}`) and a **new** stamped OUT.

## P-2 — HELPERS.json stops at v24

**LOGGED.** The builder still stamps via frozen `nfl_imv_v24.py`, so
`OUT/store/HELPERS.json` omits v26, v27, and
`nfl-imv-feature-build-v2.4.1.sh`. v27 is frozen; IMV said v27 needs
no change to launch, with P-2 logged. Do not write those pins into
the store (that would break SHA256SUMS-last).
