# week-aware-roster-step2-v1

Step 2 only (SPEC `8eb532c1` §7). INV-1 unconditional PASS `af37925e`.

This package is the revised implementation SPEC, frozen scoring-rule
delta (**none**), and the T-PIT leakage-test suite. It is **not** a
refit, not an opening, and not a source SoT pin.

| path | what |
| --- | --- |
| `SPEC.md` | implementation SPEC (G-PIT, reconstruction, missingness) |
| `scoring-rule-delta.md` | **None** — K-*/I-* unchanged |
| `STOP.md` | hard stops still in force |
| `leakage/fixtures/` | T-PIT-1..7 + feature manifest + 2863-key schedule |
| `leakage/expected/` | answers filed **before** the harness sha |
| `leakage/code/` | week-aware reconstruction + G-PIT loader STOP + runner |
| `leakage/receipts/` | synthetic T-PIT-1..10 + development coverage |

Development reconstructible weeks = **0** until a capture-time weekly
source exists (NR-1). W1 2019–23 packs are week-label, not capture-time.
B2b 2024/25 W1 packs remain DO-NOT-OPEN.

Do not start Step 4/5/6/7.
