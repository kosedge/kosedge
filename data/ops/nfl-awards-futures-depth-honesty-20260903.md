# NFL honesty stamps — Awards vs Futures + Depth vs Camp — 2026-09-03

**Status:** Copy/stamp only. Tiles stay visible. Paywall off. No KEI mint. No remat. No new products. Draft PR — CoS merges.

## Bugs (paying-subscriber honesty)

1. **Awards vs Futures** — `/pro/nfl/awards` (model award-score snapshot) and `/pro/nfl/projections` (Futures) can disagree on the same player / different vintages.
2. **Depth Charts vs Camp** — `/pro/nfl/depth-charts` (and team hub depth) can name a different QB1 than Camp Desk notes (IR / claims).

## Fix

| Surface | Stamp |
|---------|--------|
| Awards | `NFL_AWARDS_SOURCE_STAMP` — model award-score snapshot + as-of; separate from Futures; player award odds not joined |
| Futures | `NFL_FUTURES_SOURCE_STAMP` — season sim / player-production spine + as-of; separate from Awards; odds not joined |
| Depth Charts | `NFL_DEPTH_SOURCE_STAMP` — packaged/model depth, **not live Camp Desk**; Camp Desk link for named QB1/IR/claims |

Shared constants: `apps/web/lib/nfl-surface-honesty.ts`.

## Explicit non-goals

- Do **not** silently reconcile Awards ↔ Futures numbers or mint a combined ranking
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
