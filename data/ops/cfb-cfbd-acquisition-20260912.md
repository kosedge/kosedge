# CFBD acquisition / coverage audit — Data Layer v2

**Generated:** `2026-09-13T03:35:35Z`
**Production MATCHUP_RESPONSE:** `1.4` (unchanged)
**Kill switch:** `OFF`  **#532:** DO NOT MERGE
**Key present:** `True`  **Calls used:** `1` / `12`
**Bulk ingest:** `False`  **HIGH_ENV rerun:** `False`  **Opened 2025:** `False`

## Decision

**CFBD_AUTH_FAILED_DO_NOT_INGEST**

Ship: **false**. Winner: **none**. PLAY: **false**.

The stored server-side key was rejected (HTTP 401) on every probe. Do not guess the key. Put the exact generated value in the gitignored local env file. Do not paste it into chat. The feature map below is from official CFBD docs and remains the plan.

This is an acquisition report. The scoring model was not modified. No 40–60% capture target. Free-tier budget is 1,000 requests/month; this audit used a 12-call probe only.

## Auth diagnosis

Calls consumed this rerun: `1`. Fail-fast is on: the first 401 stops the remaining probes.

Header scheme: `Authorization: Bearer <CFBD_API_KEY>`. Matches official CFBD docs: `True`.
401 body: `{"message":"Unauthorized"}`. WWW-Authenticate: `None`.

Official CFBD docs and cfbd-python require Bearer plus a space. The client already sends that. A 401 with body {"message":"Unauthorized"} and no WWW-Authenticate means CFBD rejected the secret, not the header scheme. Do not retry variants.

Required-field inventory and historical coverage from live payloads are unavailable until a probe returns 200. The feature map below remains docs-only. The 52-call first pass is not authorized.

## Feature map

| v2 need | CFBD source | classification | point-in-time note |
|---|---|---|---|
| true_pace_plays | `/stats/season/advanced` | **DIRECT** | endWeek=W-1 rolling snapshot. Week 1 is missing. |
| seconds_per_play | `/plays` | **DERIVABLE_FROM_PBP** | One /plays call per year+week. Derive only from week < W. |
| off_def_ppa | `/stats/season/advanced + /ppa/games` | **DIRECT** | Prefer advanced endWeek=W-1. /ppa/teams is full-season — do not use mid-year. |
| success_rate | `/stats/season/advanced` | **DIRECT** | endWeek=W-1 |
| explosiveness | `/stats/season/advanced` | **DIRECT** | CFBD explosiveness, not 50+0.15*(off-def). |
| pass_rush_explosiveness | `/stats/season/advanced` | **DIRECT** | endWeek=W-1 |
| explosive_plays_created_allowed | `/plays` | **DERIVABLE_FROM_PBP** | Define explosive from raw plays with week < W. Do not invent a proxy if PBP not pulled. |
| havoc | `/stats/season/advanced` | **DIRECT** | endWeek=W-1 |
| finishing_ppp | `/stats/season/advanced` | **DIRECT** | endWeek=W-1. Off and def both present. |
| field_position | `/stats/season/advanced` | **DIRECT** | endWeek=W-1 |
| stuff_power_line_yards | `/stats/season/advanced` | **DIRECT** | endWeek=W-1 |
| game_advanced | `/stats/game/advanced` | **DIRECT** | Use only games with week < W when building a snapshot. |
| drives | `/drives` | **DIRECT** | Year+week. Reconstruct finishing from week < W. |
| returning_production | `/player/returning` | **DIRECT** | Season-Y preseason snapshot. Legal for all weeks of Y. |
| qb_player_success | `/ppa/players/season + /stats/player/season` | **DIRECT** | Player season endpoints may leak later weeks unless startWeek/endWeek used. |
| stats_player_success | `/stats/player/success` | **UNAVAILABLE** | Not in the current public swagger. Do not call blindly. |
| weather | `/games/weather` | **UNAVAILABLE** | Swagger marks this Patreon-only. Free tier should treat as missing. |
| sp_plus | `/ratings/sp` | **EXTERNAL_RATING** | Season-level, no throughWeek. Same-season SP+ leaks future games. Prior-year only, or diagnostic. |
| core_opponent_adjusted | `/ratings/core` | **POINT_IN_TIME_RISK** | throughWeek exists, but CFBD says historical CORE is retrospective methodology, not a live archive. |
| betting_lines | `/lines` | **POINT_IN_TIME_RISK** | Diagnostic only. Never a HIGH_ENV v2 predictor. |

## Request budget (research universe, not this audit)

Train-0 / Val-0 / Val-1 = 2022–2024 weeks 1–14.

| work | estimated calls |
|---|---:|
| rolling `/stats/season/advanced` endWeek=1..14 × 3 seasons | 42 |
| `/games` schedule × 3 seasons | 3 |
| `/player/returning` 2021–2024 | 4 |
| `/ratings/sp` prior-year benchmark only | 3 |
| **first pass (no PBP, no CORE)** | **52** |
| optional CORE throughWeek snapshots | 42 |
| deferred `/plays` one-call-per-week | 42 |
| free-tier monthly ceiling | 1000 |

First-pass ingest fits in ~52 calls. Do not pull PBP until rolling advanced stats are frozen and reviewed. Owned SportsDataverse PBP already covers 2021–2024 on the HD lake for custom explosive-rate work.

## Probe results

| id | endpoint | status | rows | bytes | error |
|---|---|---:|---:|---:|---|
| adv_2022_endw3 | `/stats/season/advanced` | 401 | — | 26 | HTTP 401 |

## Ingestion architecture (proposed, not executed at scale)

```
CFBD_API_KEY (server env)
  → GET /stats/season/advanced?year=Y&endWeek=W-1
  → immutable raw lake  raw/cfbd/stats_season_advanced/year=Y/
  → normalized team-week  clean/cfbd/team_week/team_week_Y_through_WW.json
  → HIGH_ENV join later (not this commit)
```

Every team-week row carries `season`, `through_week`, `team`, `source`, `source_version`, `is_point_in_time_safe`. Week 1 current-season values are missing. Never 50-fill.

SP+ is an external benchmark and only legal as a **prior-year** feature. CORE is research-only until a live-archive vs retrospective test exists. `/lines` is diagnostic. `/games/weather` is Patreon-only on the public swagger.

## What this is not

- Not a production change.
- Not a new MATCHUP_RESPONSE, α, A1, E3, or C2.
- Not a HIGH_ENV rerun.
- Not bulk CFBD ingestion.
- Not permission to open 2025 or turn the board on.
- Not a frontend/browser CFBD integration.

