# Club Desk — Tuesday 2026-09-22 (MNF drop + IR amend)

**Lock:** weekday Club Desk authority — real-news clubs only  
**Institutional memory:** `no prior grades` (`data/knowledge/nfl/week-preview/` empty)

## Current week (fail closed)

Helper: `apps/web/lib/nfl-current-week.ts` against `nfl-canonical-schedule-2026`.

| Clock | Result |
| --- | --- |
| Now 2026-09-22 afternoon ET | **Week 3 REG** · `proven: true` · `reason: prior_week_final` |
| Week 2 last | `2026-W02-NYG@LAR` kickoff 2026-09-22T00:15Z · FINAL at +4h = 2026-09-22T04:15Z |
| Week 3 first | `2026-W03-ATL@GB` kickoff 2026-09-25T00:15Z (Thu 8:15p ET) |

Do **not** pin Week 2. Post-MNF Tuesday is Week 3.

## Package

`content/writers/camp-desk-2026/2026-09-22.json`

- `package: daily` · date-only titles · Club Desk wrap chrome
- 6 news clubs: NYG / LAR (required MNF) + CHI / WAS / LAC / MIN (Mon IR/availability)
- Quiet skip: DEN (Over 2/5 KEEP unchanged) and the rest
- Singular `preview_delta` ×6 — NYG/LAR `touched`, CHI/WAS/LAC/MIN `flagged`
- All Pass; DEN Over 2/5 KEEP unchanged (DEN club not in this amend)
- Coming soon ON — no minted KEI · no PLAY/LEAN · no tweet/X URLs · no win-total restamp

## Product path (verify)

- Canonical: `/pro/nfl/club`
- Legacy: `/pro/nfl/camp` → `/pro/nfl/club`
- Week badge uses `resolveCurrentNflRegWeek()` (not a hard pin)
- Shelf loads newest `desk_date` (2026-09-22) with source hrefs + KosEdge date stamp

## Expected smoke (post-deploy)

| Check | Expect |
| --- | --- |
| `GET /pro/nfl/club` | **200** |
| `GET /pro/nfl/camp` | **307** → `/pro/nfl/club` |
| Week badge | **Week 3** |
| Shelf | wrap + **6** notes · `data-desk-date=2026-09-22` |
| Unit | `nfl-current-week` + `nfl-camp-desk-daily` green |

Fail-closed paths not hit when week proven + package schema valid + route live.
