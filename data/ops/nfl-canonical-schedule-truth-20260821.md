# Canonical NFL schedule truth (2026-08-21)

One REG pack owns kickoff, venue, week, and team IDs. Product boards format `kickoff_utc` → ET. Odds commence may differ; **canonical wins for display**.

## Pack

- `apps/web/lib/nfl-canonical-schedule-2026.json` — 272 REG games, 32 teams
- Loader: `apps/web/lib/nfl-canonical-schedule.ts`
- Resolver: `apps/web/lib/nfl-schedule-kickoff.ts` (`resolveNflKickoffIso`)
- Rebuild: `node scripts/nfl/build_canonical_schedule_2026.mjs scripts/nfl/sources/nfl-ops-2026-regular-season-schedule.md`
- Source: [NFL Football Operations 2026 regular-season schedule](https://operations.nfl.com/calendar-events/nfl-schedule/2026-regular-season-schedule/) (as_of 2026-08-21)

Join rule: fair-lines / Odds `start_time` is overlay only. If the pack has the matchup, use pack `kickoff_utc` (including `null` = official TBD). Do not invent 4:00 PM ET.

Engine `game_id` still uses LA for Rams (`2026-W01-SF@LA`). Product IDs use LAR (`2026-W01-SF@LAR`).

## Consumers

| Surface | Kickoff path |
|---------|----------------|
| Weekly Slate / KEI Lines / Edges game rows | `fetchNflFairLines` stamps canonical `startTime` |
| Edge Board | `resolveNflKickoffIso` (pack first) |
| Game Boxes / Survivor matchup list | `matchupsFromWallChart` stamps `startTime` |
| Edges prop rows | team+week lookup; only if Props surface is book-joined |

## Week 1 audit (all match)

Official clocks from NFL.com / Football Operations. KosEdge = pack `kickoff_utc` formatted America/New_York.

| game_id | kosedge kickoff_et | official kickoff_et | match | venue |
|---------|--------------------|---------------------|-------|-------|
| 2026-W01-NE@SEA | Wed, Sep 9 8:20 PM ET | Wed, Sep 9 8:20 PM ET | Y | Lumen Field |
| 2026-W01-SF@LAR | Thu, Sep 10 8:35 PM ET | Thu, Sep 10 8:35 PM ET | Y | Melbourne Cricket Ground |
| 2026-W01-ATL@PIT | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | Acrisure Stadium |
| 2026-W01-BAL@IND | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | Lucas Oil Stadium |
| 2026-W01-BUF@HOU | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | NRG Stadium |
| 2026-W01-CHI@CAR | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | Bank of America Stadium |
| 2026-W01-CLE@JAX | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | EverBank Stadium |
| 2026-W01-NO@DET | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | Ford Field |
| 2026-W01-NYJ@TEN | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | Nissan Stadium |
| 2026-W01-TB@CIN | Sun, Sep 13 1:00 PM ET | Sun, Sep 13 1:00 PM ET | Y | Paycor Stadium |
| 2026-W01-ARI@LAC | Sun, Sep 13 4:25 PM ET | Sun, Sep 13 4:25 PM ET | Y | SoFi Stadium |
| 2026-W01-GB@MIN | Sun, Sep 13 4:25 PM ET | Sun, Sep 13 4:25 PM ET | Y | U.S. Bank Stadium |
| 2026-W01-MIA@LV | Sun, Sep 13 4:25 PM ET | Sun, Sep 13 4:25 PM ET | Y | Allegiant Stadium |
| 2026-W01-WAS@PHI | Sun, Sep 13 4:25 PM ET | Sun, Sep 13 4:25 PM ET | Y | Lincoln Financial Field |
| 2026-W01-DAL@NYG | Sun, Sep 13 8:20 PM ET | Sun, Sep 13 8:20 PM ET | Y | MetLife Stadium |
| 2026-W01-DEN@KC | Mon, Sep 14 8:15 PM ET | Mon, Sep 14 8:15 PM ET | Y | GEHA Field at Arrowhead Stadium |

Zero 4:00 PM ET defaults. Opener is 8:20 ET at Lumen. Melbourne is 8:35 ET at MCG.

Flex TBD (weeks 16–18 unnamed windows) stay `kickoff_utc: null` / status `time_tbd`.

## Props ↔ Edges

Shared `nflPropsSurfaceState`: gated / empty / research-only / book-joined.

Edges shows prop-edge rows **only** when the Props board is book-joined. Otherwise the same status copy and a link to `/pro/nfl/props`. No orphan Anytime TD sheet.

## Tests

`apps/web/__tests__/lib/nfl-canonical-schedule.test.ts` — 32 / 272 / Week 1 anchors / no 4pm / canonical beats fake odds / Props flag vs Edges.
