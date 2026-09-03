# NFL Fantasy Mock / Builder recommendation fixes — 2026-09-02

**Live desk:** `/pro/nfl/fantasy` · `/pro/nfl/fantasy/mock`  
**Scope:** Grades, notable-reaches copy, ADP-aware value list. No tile hide, paywall, KEI mint, remat, Bijan matcher, or ATD.

## Bugs (GPT 6.2 #5 / CoS)

| # | Defect | Fix |
|---|--------|-----|
| 1 | Auto-complete could omit required K/DST and still award **B** | `letterGradeFromStarters`: any required hole → max **C+**. CPU pool includes needed K/DST (board-end ranks) and late need scoring fills them from R12. |
| 2 | Notable reaches used `valueDelta` (model vs ADP) but copy said pick vs ADP | Copy aligned with Notable values: `model #X vs ADP ~Y (Δ)`. |
| 3 | Builder ADP-aware value list could recommend Reach-tagged players | `bestAvailableByValueAware` excludes `valueDelta ≤ −8`; builder static timing labels reaches as reach (not take_now). |

## Code

- `apps/web/lib/fantasy/team-builder.ts` — shared `letterGradeFromStarters`
- `apps/web/lib/fantasy/mock-draft-engine.ts` — grade + reaches copy
- `apps/web/lib/fantasy/value-aware-recs.ts` — `isReachTagged` + value filter
- `apps/web/lib/fantasy/mock-cpu.ts` — need-position pool + late K/DST need

## Tests

- Incomplete K/DST → not B (builder + mock report)
- Reaches copy has `model #` / no `took at pick`
- Value list excludes Reach-tagged
- Auto-complete with K/DST board fills both slots

## Non-goals

Bijan identity (separate PR), ATD, remat, KEI, paywall, Fantasy tile.
