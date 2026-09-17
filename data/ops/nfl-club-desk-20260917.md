# Club Desk — Thursday 2026-09-17 (weekday ship)

**Lock:** weekday Club Desk authority — real-news clubs only  
**Institutional memory:** `no prior grades` (`data/knowledge/nfl/week-preview/` empty)

## Current week (fail closed)

Helper: `apps/web/lib/nfl-current-week.ts` against `nfl-canonical-schedule-2026`.

| Clock | Result |
| --- | --- |
| Now 2026-09-17 afternoon ET | **Week 2 REG** · `proven: true` · `reason: prior_week_final` |
| Week 1 last | `2026-W01-DEN@KC` FINAL |
| Week 2 first | `2026-W02-DET@BUF` kickoff 2026-09-18T00:15Z (Thu 8:15p ET) |

Do **not** pin Week 1. Pre-TNF Thursday stays Week 2.

## Package

`content/writers/camp-desk-2026/2026-09-17.json`

- `package: daily` · date-only titles · Club Desk wrap chrome
- 3 news clubs: SF / BAL / SEA (all Pass)
- Quiet skip: the other 29
- Singular `preview_delta` ×3, all `flagged`
- Pass throughout; DEN Over 2/5 KEEP + LAC Under 2/5 KEEP + KC Pass unchanged
- No minted KEI · no tweet/X URLs · no win-total restamp
- SF: surgery / ~10w IR-expected only — **no** club site IR transaction cited (none verified)
- No Fair Lines / Coming soon / model touches

## Product path (verify)

- Canonical: `/pro/nfl/club`
- Legacy: `/pro/nfl/camp` → `/pro/nfl/club`
- Week badge uses `resolveCurrentNflRegWeek()` (not a hard pin)
- Shelf loads newest `desk_date` (2026-09-17) with source hrefs + KosEdge date stamp

## Expected smoke (post-deploy)

| Check | Expect |
| --- | --- |
| `GET /pro/nfl/club` | **200** |
| `GET /pro/nfl/camp` | **307** → `/pro/nfl/club` |
| Week badge | **Week 2** |
| Shelf | wrap + **3** notes · `data-desk-date=2026-09-17` |
| Unit | `nfl-current-week` + `nfl-camp-desk-daily` green |

Fail-closed paths not hit when week proven + package schema valid + route live.
