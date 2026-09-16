# Club Desk — Wednesday 2026-09-16 catch-up (post-#557 smoke)

**Lock:** weekday 3pm OS — real-news clubs only  
**Institutional memory:** `no prior grades` (`data/knowledge/nfl/week-preview/` empty)

## Current week (fail closed)

Helper: `apps/web/lib/nfl-current-week.ts` against `nfl-canonical-schedule-2026`.

| Clock | Result |
| --- | --- |
| Now 2026-09-16 ~21:23Z / 5:23p ET | **Week 2 REG** · `proven: true` · `reason: prior_week_final` |
| Week 1 last | `2026-W01-DEN@KC` kickoff 2026-09-15T00:15Z · FINAL at +4h = 2026-09-15T04:15Z |
| Week 2 first | `2026-W02-DET@BUF` kickoff 2026-09-18T00:15Z (Thu 8:15p ET) |

Do **not** pin Week 1. Pre-TNF Wednesday stays Week 2.

## Package

`content/writers/camp-desk-2026/2026-09-16.json`

- `package: daily` · date-only titles · Club Desk wrap chrome
- 9 news clubs since #565 Tue afternoon amend: MIN / SF / ARI / KC / MIA / CLE / DET / BUF / ATL
- Quiet skip: the other 23
- Singular `preview_delta` ×9, all `flagged`
- Pass throughout; DEN Over 2/5 KEEP + LAC Under 2/5 KEEP + KC Pass unchanged
- No minted KEI · no tweet/X URLs · no win-total restamp

## Product path (verify)

- Canonical: `/pro/nfl/club`
- Legacy: `/pro/nfl/camp` → `/pro/nfl/club`
- Week badge uses `resolveCurrentNflRegWeek()` (not a hard pin)
- Shelf loads newest `desk_date` (2026-09-16) with source hrefs + KosEdge date stamp
