# CoS handoff — week-aware roster Step 2 v2

Route to IMV for **Step 3 only**. Step 4 is NOT authorized.

## Pins

| item | sha8 |
| --- | --- |
| IMV SPEC | `8eb532c1` |
| IMV Step 3 RETURN (v1) | `da9a95b6` |
| v1 MANIFEST | `d6484094` |
| Expected answers commit | `1643d3ca` |
| Harness commit | `caf6cf16` |
| D-4 path | **(ii)** SPEC erratum |
| Scoring-rule delta | **none** |

MANIFEST sha8 is the CoS → IMV handle. See `MANIFEST` / `SHA256SUMS`.

## Recover

`/workspace/ops/nfl_injury_audit_t4274u/week-aware-roster-step2-v2/`

Required agent store (must exist before "deposited"):

`/cursor/stores/self/artifacts/week-aware-roster-step2-v2/`

Repo mirror: `artifacts/week-aware-roster-step2-v2/` (PR #630)

## Result

- T-PIT-1..10 **PASS** on synthetic; receipts reproducible from deposited harness
- Development coverage: reconstructible **0** / ineligible **2863** (export keys)
- T-PIT-10 hits cited `8d188da2` / `247744d2`
- No refit, no opening, no lock, no 2024/25 read, no source SoT pin

## Split

`notes/verified-vs-claimed.md`
