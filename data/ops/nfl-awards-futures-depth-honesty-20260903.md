# NFL honesty stamps — Awards vs Futures + Depth vs Camp — 2026-09-03

**Status:** Copy/stamp only. Tiles stay visible. Paywall off. No KEI mint. No remat. No new products. Draft PR — CoS merges.

## Bugs (paying-subscriber honesty)

1. **Awards vs Futures** — `/pro/nfl/awards` (model award-score snapshot) and `/pro/nfl/projections` (Futures) can disagree on the same player / different vintages.
2. **Depth Charts vs Camp** — `/pro/nfl/depth-charts` (and team hub depth) can name a different QB1 than Camp Desk notes (IR / claims).

## Fix

| Surface | Subscriber-facing stamp |
|---------|-------------------------|
| Awards | Model award-score snapshot from last materialize. Separate from Futures (different ranking / vintage). Player award odds not joined. |
| Futures | Season sim / player-production spine. Separate from Awards. Leader odds not joined. |
| Depth Charts | Packaged model depth chart — not live Camp Desk. Named QB1, IR, and claims live on Camp Desk. |

Shared constants: `apps/web/lib/nfl-surface-honesty.ts` (page strings = subscriber English; engineering doctrine stays in file comments / ops note only).

## Explicit non-goals

- Do **not** silently reconcile Awards ↔ Futures numbers or mint a combined ranking (engineering rule — not on-page copy)
- Do **not** join player award odds (still not joined — PR #414 Overview copy kept)
- Do **not** rewrite Camp Desk notes
- Do **not** hide Depth Charts / Awards / Futures tiles
- No Overview catalog rewrite beyond keeping #414 honest labels
- No paywall, KEI, remat, ATD, Bijan, Mock, DFS, Guillotine, CLV

## Tests

```bash
pnpm --filter @kosedge/web exec vitest run \
  __tests__/lib/nfl-surface-honesty.test.ts \
  __tests__/components/pro/NflIntelTablePage.test.tsx
```
