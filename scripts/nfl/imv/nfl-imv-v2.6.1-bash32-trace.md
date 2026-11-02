# v2.6.1 — bash 3.2 empty-array stop (PACK_ARG)

Mac `/bin/bash` is 3.2.57. Under `set -u`, `"${empty[@]}"` is fatal.

## Audit (three IMV v2.4 shells; frozen, not edited)

| Shell | Array expansions | Empty-array risk |
| --- | --- | --- |
| `nfl-imv-feature-build-v2.4.sh` | `"${PBP_ARGS[@]}"` (l.250), `"${PACK_ARG[@]}"` (l.254). `PACK_ARG=()` unless `--pack`. | **Yes.** W4 stopped here. |
| `nfl-imv-sealed-v2.4.sh` | none | No |
| `nfl-imv-prestage-nflverse.sh` | `"${FILES[@]}"` (l.105). `FILES` is a 4-entry literal. `W6_PRODUCT` is never expanded with `[@]`. | No (never empty) |

`${#PBP_ARGS[@]}` is a length read after the array is assigned; not the fatal form.

## Fix (new files only)

`nfl-imv-feature-build-v2.4.1.sh` uses `${PACK_ARG[@]+"${PACK_ARG[@]}"}` and the same idiom for `PBP_ARGS`. Frozen v2.4.sh is unchanged.

## check-pins

v26 `SHELL_PINS` is frozen to the three v2.4 shells. Pinning v2.4.1 required **new helper** `nfl_imv_v27.py`.
