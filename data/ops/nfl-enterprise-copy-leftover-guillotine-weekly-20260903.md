# NFL enterprise leftover copy — Guillotine + Weekly Fantasy pages — 2026-09-03

**Live after PR 414:** Overview tiles were honest; destination pages still sold unfinished products.  
**Scope:** Copy only. Tiles stay visible/clickable. No waiver/DFS/Guillotine product build. Paywall off. No KEI mint. No remat.

## Bugs

| Surface | Dishonest copy | Fix |
|---------|----------------|-----|
| `/pro/nfl/fantasy/guillotine` | “Last place is eliminated each week…”, “lowest-scoring team is cut”, “Waivers and opportunistic adds matter weekly” | Educational stay-alive lists from season ranks — matches Overview 414 hint |
| `/pro/nfl/weekly-fantasy` | H1 “Weekly Fantasy Projections” / H2 “Weekly leaders” while body already said season-rate PPG | H1 **Weekly Fantasy**; H2 **Season-rate PPG leaders**; subtitle aligned to season-rate / not week-specific |

## Code

- `apps/web/app/(pro)/pro/nfl/fantasy/guillotine/page.tsx`
- `apps/web/app/(pro)/pro/nfl/weekly-fantasy/page.tsx`
- `apps/web/lib/fantasy/guillotine.ts` (comment honesty only)
- `apps/web/__tests__/lib/pro-sport-ia.test.ts` — destination page source asserts

## Non-goals

Tile hide, paywall, KEI mint, remat, waiver/DFS/Guillotine product build.

**Do not merge** — CoS merges.
