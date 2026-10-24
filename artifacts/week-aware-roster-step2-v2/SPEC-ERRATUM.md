# SPEC erratum (D-4 path ii) — synthetic-only T-PIT while NR-1 is open

Parent SPEC: `8eb532c1` §6 / §7.
This erratum is submitted for IMV judgment as part of Step 2 v2.
It does **not** authorize Step 4, a source SoT pin, opening, or spend.

## D-4 path chosen: **(ii)**

INV-1 established there is no archived capture-time weekly
roster/depth/transaction book for pre-2024 development (NR-1).
Reconstructible weeks = 0. Safe <=2023 **weekly** extracts with
`availability_ts` do not exist to run T-PIT against.

Path (i) — run T-PIT on approved <=2023 development extracts — would
require inventing weekly coverage or treating week-label W1 packs as
capture-time. Both are forbidden.

Therefore this resubmission asks IMV to adopt, **while NR-1 is open**:

> Step 2 leakage bar = T-PIT-1..10 **PASS on synthetic 2098/2099**
> **plus** development **ineligibility coverage** (schedule-export keys
> counted; reconstructible=0; W1 week-label ineligible; B2b unopened).
> T-PIT execution on development weekly extracts is deferred until a
> capture-time source exists and is pinned after IMV review.

This is not a silent omit: the development leg is the coverage report,
not a hidden T-PIT skip.

## D-7 deferred items (same erratum path)

Strengthened in v2 (not deferred):

- T-PIT-4: before-cutoff PS promotion **success** case added
- T-PIT-9: **cross-process** re-run (two subprocesses)
- T-PIT-8: **live scan** of deposited `week_aware_roster.py` for
  injuries / rosters / depth / transactions

Still deferred until a live feature pipeline exists (NR-1 / no SoT pin):

- T-PIT-8 live scan of `qb_changes` / `odds` / `weather` pipelines
  (manifest still requires `availability_ts` or Ryan-exempt; none exempt)

## What this erratum does not do

- Does not change G-PIT, reconstruction rules, or K-*/I-* gates
- Does not mark any development week reconstructible
- Does not authorize Odds API / roster-data spend
- Does not reopen 2024/25
