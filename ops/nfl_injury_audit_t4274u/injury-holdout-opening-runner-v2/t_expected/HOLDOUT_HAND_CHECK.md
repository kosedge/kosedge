# Holdout expected answers v2 — hand check (filed before the runner)

Gate table + lock fields + receipt schema + record/HFA baseline method.
**No holdout values.** `holdout_values` is null.

Filed against IMV RETURN `a8958e85`. Real lock not written. No 2024/25 byte.

## Baseline (request v3.1 §2)

Record/HFA as in the v6 scorer `inputs/record_baseline_le2023.csv` method
(sha `502110cf`). Prior-week W-L only; ties ignore; HFA 1.05; BASE_TOTAL 45.3;
rest 7/7; injury None. Week-1 0-0 identity: `record_spread = -1.05`,
`record_total = 44.8435`. `baseline_margin = -record_spread`.
Hardcoded `-3.0` / `45.0` is forbidden. `residual_complete` is not hardcoded.

## Lock

Every field in `lock_fields` (a8958e85 EXACT PINS). Production path
`/workspace/ops/nfl_injury_audit_t4274u/holdout-once.lock` exists in code and
is enabled only by a verified IMV PASS sha (absent this package). Lock stays
0444; consumption is `holdout-once.lock.consumed`.

## Receipt

Every field in `receipt_schema` (R-7). Writer emits it.

## Fixtures

`F-E2E` is lock → export (writer `9947b880`) → guards → join → score → receipt
on synthetic 2022, copied to a temp dir. Default `--mode holdout` STOPs
`O-1 opening blocked` and does not write the real lock.
