# Week-aware roster reconstruction spec v1 (Phase 1)

Ryan t4344u OPTION B (`47afd7f6`). Inventory:
`artifacts/injury-roster-leakage-inventory-v1/`.

This is a specification for IMV. It is **not** a rebuild and **not** a
refit. Phase 2 (reconstruct + refit on approved pre-2024 development
data only) waits for IMV to accept this spec or return the exact gaps.

## Contents

- `SPEC.md` — sources, as-of timestamps, cutoff, missing→ineligible
- `leakage-controls.md` — Ryan's permanent rule, all time-sensitive features
- `required-tests.md` — NFL automated tests including B-4b(n)-PIT
- `synthetic-cases/` — fixtures the current collapse fails and the
  rebuild must pass
- `notes/imv-acceptance-gate.md` — what "accept" means; what we will
  not start until then
