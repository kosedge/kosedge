# NCAAM ESPN Schedule SoT (Option A) — 2026-09-04

**Scope:** Production spine track — ESPN scoreboard package + reader + fail-closed B7 map.
**Not in scope:** Edge Board populate, PLAY/Conf%/props, Odds densify, KenPom-as-SoT, #12 GO-2.

Closes the **B7.5 Schedule SoT gap** named in `data/ops/ncaam-identity-b7-20260904.md` (Option A).

## Paths

| Piece | Path |
| ----- | ---- |
| Ingest | `scripts/ncaam/ingest_espn_official_schedule.py` |
| ESPN→B7 map helper | `apps/web/src/ncaam_espn_schedule_map.py` (uses `ncaam_identity` + `aliases.json`) |
| Reader | `services/model-service/src/services/ncaam_schedule/official_schedule.py` |
| Pack 2022-23 | `…/ncaam_schedule/data/ncaam_official_schedule_2022_23.json` |
| Pack 2023-24 (Lab early) | `…/ncaam_schedule/data/ncaam_official_schedule_2023_24.json` |
| Tests | `services/model-service/tests/test_ncaam_official_schedule.py` |
| TS map tests | `apps/web/__tests__/lib/ncaam-espn-schedule-map.test.ts` |

**Endpoint used:** `https://site.web.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard` (`groups=50`, `limit=500`). `site.api.espn.com` 403'd from this agent egress after burst; web API retained historical `dates=YYYYMMDD`.

## Season coverage (Lab tip window)

Lab LOCKED universe tip window: **2022-11-01 → 2024-01-28**.

| Pack | Window ingested | ESPN events | B7 both-sides mapped | `slate_complete` |
| ---- | --------------- | ----------- | -------------------- | ---------------- |
| 2022-23 | 2022-11-01 → 2023-04-10 | 6261 | 1300 | **false** |
| 2023-24 | 2023-11-01 → 2024-01-28 | 3954 | 660 | **false** |

Refresh:

```bash
python scripts/ncaam/ingest_espn_official_schedule.py --season 2022-23
python scripts/ncaam/ingest_espn_official_schedule.py --season 2023-24 --end-date 2024-01-28
```

## Map miss rate (honesty)

B7 `aliases.json` is a curated high-major / odds-facing universe (~125 team_ids), **not** full D1.

| Pack | `map_miss_rate` (events with ≥1 unmapped/ambiguous side) |
| ---- | -------------------------------------------------------- |
| 2022-23 | **79.2%** |
| 2023-24 (thru 2024-01-28) | **83.3%** |

Unmapped ESPN sides are **omitted** (fail-closed). Top miss examples include mid-majors not yet in aliases (UAB, Charlotte, Furman, …). Expanding aliases raises coverage; it must stay fail-closed (no fuzzy invent).

**`slate_complete`:** always **false** on these packs. Thin / B7-mapped subset ≠ complete D1 slate. Do not stamp true without an honest densified full join.

## Miami FL ≠ Miami OH (schedule names)

| ESPN label | B7 `team_id` | ESPN team id |
| ---------- | ------------ | ------------ |
| Miami Hurricanes | `miami fl` | 2390 |
| Miami (OH) RedHawks | `miami oh` | 193 |
| bare `Miami` / location-only | **omit** | — |

Pack receipts:

- 2022-23: miami_fl=31 mapped games, miami_oh=12 mapped games (distinct ids; zero bare `miami` rows)
- 2023-24 early: miami_fl=15, miami_oh=4
- Example OH: `401493739` 2022-12-03 Indiana State @ Miami (OH)
- Example FL: `401479680` 2022-12-01 Rutgers @ Miami Hurricanes

## Lab join note

Schedule SoT LOCKED Option A for production spine. **Lab interim joins still use Odds `event_id` (D).**

Each game row exposes:

- `game_id` / `espn_game_id` — stable ESPN event id
- `odds_event_id: null` — crosswalk stub for future E hybrid

**Do not invent** Odds↔ESPN links without evidence.

## Game row shape (CFB-adjacent)

`game_id`, `espn_game_id`, `tipoff` (+ `kickoff` alias), `date`, `home`/`away` (B7 ids), `home_name`/`away_name`, `home_espn_id`/`away_espn_id`, `venue`(+ city/state), `neutral_site`, `conference_game`, `status`, scores when final, `season_type`, `odds_event_id=null`.

## Explicit non-goals (HOLD)

- Edge Board populate / assemble fill
- PLAY / Conf% / props
- Odds densify pulls
- Invented tips or dual game rows
- KenPom-as-SoT
- Claiming `slate_complete=true` on this mapped subset
