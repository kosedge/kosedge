# CoS handoff — week-aware roster Step 2

Route to IMV for **Step 3 only** (SPEC `8eb532c1` §7). Do not start Step 4–7.

## Pins

| item | sha8 |
| --- | --- |
| IMV SPEC | `8eb532c1` |
| INV-1 unconditional PASS | `af37925e` |
| INV-1 base MANIFEST | `7d93380e` |
| INV-1 erratum MANIFEST | `396800e3` |
| Expected answers commit | `52879746` |
| Harness commit | `3f226966` |
| Scoring-rule delta | **none** |

MANIFEST sha8 is the CoS → IMV handle. See `MANIFEST` / `SHA256SUMS` in this directory.

## Recover

CoS recovers this package to:

`/workspace/ops/nfl_injury_audit_t4274u/week-aware-roster-step2-v1/`

Required agent store (must exist before "deposited"):

`/cursor/stores/self/artifacts/week-aware-roster-step2-v1/`

Repo mirror (this PR): `artifacts/week-aware-roster-step2-v1/`

## Result

- T-PIT-1..10 **PASS** on synthetic
- Development coverage: reconstructible **0** / ineligible **2863**
- No refit, no opening, no lock, no 2024/25 read, no source SoT pin

## Split

`notes/verified-vs-claimed.md` — verified receipts vs claimed (not production truth).
