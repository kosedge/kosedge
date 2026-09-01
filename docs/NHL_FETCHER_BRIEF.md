# NHL fetcher — raw snapshots (Pick B)

**Phase:** Ingest. **No** shrink. **No** prior pack. **No** board emit.  
**Depends on:** Ch0 / #390 merged (Pick **B**).  
**Stamp:** `nhl-fetcher-v1`  
**SoT / vendor:** official NHL only (`*.nhle.com`) — one vendor.  
**KEINHL:** stays blank. Do not fill `/edge-board/nhl` KEI.

Ch1 reads these files later and picks one `s`. **Not this PR.**

---

## Source URLs

| Asset                 | Endpoint                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| Schedule (2026–27 RS) | `GET https://api-web.nhle.com/v1/club-schedule-season/{TEAM}/20262027` (32 clubs, dedupe `gameType=2`)  |
| Team GF/GA (2025–26)  | `GET https://api-web.nhle.com/v1/standings/now`                                                         |
| Skater seasons 23–26  | `GET https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=seasonId={YYYYYYYY} and gameTypeId=2` |
| Goalie seasons 23–26  | `GET https://api.nhle.com/stats/rest/en/goalie/summary?cayenneExp=seasonId={YYYYYYYY} and gameTypeId=2` |

Host family is NHL (`api-web.nhle.com` + `api.nhle.com/stats/rest`). No SportsData requirement. No MoneyPuck / NST.

---

## Field map

### `nhl_schedule_2026.json` → `games[]`

| Field                       | Source                                |
| --------------------------- | ------------------------------------- |
| `game_id`                   | `id`                                  |
| `game_date`                 | `gameDate`                            |
| `start_time_utc`            | `startTimeUTC`                        |
| `game_type`                 | `gameType` (2 = RS)                   |
| `game_state`                | `gameState`                           |
| `away` / `home`             | `awayTeam.abbrev` / `homeTeam.abbrev` |
| `away_score` / `home_score` | team `score` (null until played)      |

### `nhl_team_box_2025.json` → `teams[]`

| Field                                      | Source (standings/now)    |
| ------------------------------------------ | ------------------------- |
| `team`                                     | `teamAbbrev.default`      |
| `gf` / `ga`                                | `goalFor` / `goalAgainst` |
| `games_played`                             | `gamesPlayed`             |
| `wins` / `losses` / `ot_losses` / `points` | standings columns         |

### `nhl_skater_box_2023_2025.json` → `by_season[seasonId][]`

| Field                          | Source                                         |
| ------------------------------ | ---------------------------------------------- |
| `player_id`                    | `playerId`                                     |
| `player_name`                  | `skaterFullName`                               |
| `team`                         | `teamAbbrevs`                                  |
| `g` / `a` / `p` / `sog` / `gp` | goals / assists / points / shots / gamesPlayed |

### `nhl_goalie_box_2023_2025.json` → `by_season[seasonId][]`

| Field                                    | Source                                                             |
| ---------------------------------------- | ------------------------------------------------------------------ |
| `player_id`                              | `playerId`                                                         |
| `gaa` / `sv_pct` / `saves` / `gp` / `gs` | goalsAgainstAverage / savePct / saves / gamesPlayed / gamesStarted |

---

## Paths

```text
services/model-service/src/services/nhl_data.py
services/model-service/src/services/nhl_season_engine/data/
  nhl_schedule_2026.json
  nhl_team_box_2025.json
  nhl_skater_box_2023_2025.json
  nhl_goalie_box_2023_2025.json
scripts/nhl/fetch_raw.py
```

---

## Refresh command

```bash
python3 scripts/nhl/fetch_raw.py
python3 scripts/nhl/fetch_raw.py --status
```

---

## Allowlist

- `nhl_data.py` + raw JSON snapshots above
- This doc
- `scripts/nhl/fetch_raw.py`
- NHL-only CI

## Forbidden

- `NHL_TEAM_CARRY_SHRINK` · `nhl_team_prior_2026.json`
- KEI / Edge tags · filling blank KEINHL
- xG from MoneyPuck / NST
- NBA / WNBA / CFB / NFL files

## Gates

- 32 team rows for 2025–26
- Skaters + goalies for 23–24 / 24–25 / 25–26 from the same API family
- Schedule covers opening night **Sep 29** (**FLA@CAR** present); 84 games / team
- `/edge-board/nhl` KEI still blank
- NBA / WNBA / CFB numbers untouched

## Done

Raw files on disk. **Stop.** Chapter 1 is a separate PR.
