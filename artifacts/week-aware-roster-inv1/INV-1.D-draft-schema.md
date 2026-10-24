# INV-1.D — draft week-aware schema

Draft only. Not an implementation pin. Missingness is first-class.

## Keys

```
game_id              season_week_away_home (existing)
season               int
week                 int  (REG 1–18)
team                 alias-normalized
player_id            gsis_id
```

## Membership row (`roster_membership_week`)

| column | meaning |
| --- | --- |
| season, week, game_type, team, player_id | grain |
| status | ACT / DEV / RES / CUT / INA / … as published |
| availability_ts | UTC aware; capture or publication time from pinned provenance |
| availability_ts_kind | capture \| publication \| provider_as_of |
| source_uri | pin / path |
| source_sha256 | of the source file |
| missingness | OK \| MISSING_ROW \| MISSING_TS \| INELIGIBLE_PLAYOFF_FOR_REG \| SUPERSEDED_SEASON_SNAPSHOT |

Join to game: `(season, week, team)` + `availability_ts <= prediction_cutoff`.
Playoff `game_type` rows are ineligible for REG games.

## Depth / role row (`depth_role_week`)

| column | meaning |
| --- | --- |
| season, week, game_type, team, player_id, position | grain |
| depth_order | 1 = starter for that position group; not `STARTER_SLOTS` token |
| role | starter \| backup \| depth \| unknown |
| availability_ts, availability_ts_kind, source_uri, source_sha256 | same as membership |
| missingness | OK \| MISSING_ROW \| MISSING_TS \| INELIGIBLE |

`value` / QB1 are derived only from an OK depth_order row. Default
depth=2 is forbidden.

## Transaction event (`txn_event`) — if a source later exists

| column | meaning |
| --- | --- |
| player_id, from_team, to_team, event_type | trade / cut / PS_up / PS_down / IR |
| availability_ts | announcement knowable-time |
| source_uri, source_sha256, missingness | |

## Game join

| column | meaning |
| --- | --- |
| game_id, season, week, home, away | |
| kickoff_utc | existing parse |
| decision_ts | optional; tighter freeze |
| prediction_cutoff | `min(kickoff_utc, decision_ts)` unless a later package freezes tighter (E) |

## Missingness codes (never invent)

| code | action |
| --- | --- |
| OK | eligible |
| MISSING_ROW | component NULL / game ineligible per null contract |
| MISSING_TS | refuse row (B-4c class); not coerced |
| INELIGIBLE_PLAYOFF_FOR_REG | ignore for REG |
| SUPERSEDED_SEASON_SNAPSHOT | hard-STOP if G-PIT mode on (T-PIT-10) |

## Cross-feature manifest (T-PIT-8)

Every time-sensitive class must declare an `availability_ts` column or
`EXEMPT-WITH-RYAN-REASON`:

injuries, rosters, depth, transactions, QB changes, odds, weather.

Undeclared class = FAIL.
