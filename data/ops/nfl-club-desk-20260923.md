# Club Desk — Wednesday 2026-09-23 (IR/availability amend)

**Lock:** weekday Club Desk authority — real-news clubs only  
**Institutional memory:** `no prior grades` (`data/knowledge/nfl/week-preview/` empty)

## Current week (fail closed)

Helper: `apps/web/lib/nfl-current-week.ts` against `nfl-canonical-schedule-2026`.

| Clock | Result |
| --- | --- |
| Now 2026-09-23 afternoon ET | **Week 3 REG** · `proven: true` · `reason: prior_week_final` |
| Week 2 last | `2026-W02-NYG@LAR` FINAL |
| Week 3 first | `2026-W03-ATL@GB` kickoff 2026-09-25T00:15Z (Thu 8:15p ET) — not yet kicked |

Do **not** pin Week 2. Wednesday of Week 3 stays Week 3.

## Package

`content/writers/camp-desk-2026/2026-09-23.json`

- `package: daily` · date-only titles · Club Desk wrap chrome
- 5 news clubs: NYG / CHI / LAC / ATL / ARI
- Quiet skip: WAS / SEA Bradford / DEN (Over 2/5 KEEP unchanged) and the rest
- Singular `preview_delta` ×5 — NYG/CHI/LAC `touched`, ATL/ARI `flagged`
- All Pass; DEN Over 2/5 KEEP unchanged (DEN club not in this amend)
- Coming soon ON — no minted KEI · no PLAY/LEAN · no tweet/X URLs · no win-total restamp

## Product path (verify)

- Canonical: `/pro/nfl/club`
- Legacy: `/pro/nfl/camp` → `/pro/nfl/club`
- Week badge uses `resolveCurrentNflRegWeek()` (not a hard pin)
- Shelf loads newest `desk_date` (2026-09-23)

## Expected smoke (post-deploy)

| Check | Expect |
| --- | --- |
| `GET /pro/nfl/club` | **200** |
| `GET /pro/nfl/camp` | **307** → `/pro/nfl/club` |
| Week badge | **Week 3** |
| Shelf | wrap + **5** notes · `data-desk-date=2026-09-23` |
| Unit | `nfl-current-week` + `nfl-camp-desk-daily` green |
