# Stage-2 detection gap — INC-2026-09-08

## What failed to catch this

Customer-facing Fair / Book / Edge identity + selected-side **sign** bugs on the NFL Edges desk (and the shared display contract risk across sports) were caught by **human/customer review**, not by Academy / P14 automated Stage-2 detection.

## Gap statement (for Stage-2 evidence report)

Stage-2 scanners did not include a **full-slate customer-truth audit** that asserts, for every Edge Board sport and every Edges-desk handicap/total row:

1. Selected-side advantage display is a **positive magnitude** (never green-negative for the selected side).
2. Displayed market line **===** the market line used to compute the edge (same source / timestamp / run identity).
3. `abs(fair − displayed_market)` agrees with painted edge within display tolerance, else **fail closed**.
4. Moneyline and totals use **documented separate formulas** (not the spread abs rule applied blindly).

## Remediation shipped with this incident

- Shared contract module + full-slate regression auditors in `apps/web/lib/edge-board-customer-truth.ts`
- Vitest coverage across all seven Edge Board sports’ audit helpers
- Incident receipt under `docs/incidents/INC-2026-09-08-NFL-EDGE-BOARD-CUSTOMER-TRUTH/`

## Ask for Stage-2 owners

Wire the new auditors into Academy/P14 scheduled slate scans so this class cannot rely on customer eyes again.
