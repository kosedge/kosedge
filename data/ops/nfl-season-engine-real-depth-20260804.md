# NFL Season Engine — Real 2026 Depth Chart Cutover

**Date:** 2026-08-04  
**Engine version:** `nfl-season-engine-v1.9.1-real-depth`  
**Branch:** `feat/nfl-season-engine-real-depth` → `deploy-vercel`  
**Prerequisite:** v1.9 real schedule cutover (PR #86)

## Confirmation

| Field | Value |
| --- | --- |
| `mode` | `real` |
| `schedule_source` | `packaged_wall_chart_2026` (or `nfl_dp_schedules` when DB filled) |
| `schedule_game_count` | 272 |
| `depth_source` / `roster_source` | `packaged_nflverse_depth_2026` (offline / empty DB) |
| `depth_as_of` | `2026-08-03` |
| Named skill teams | **32 / 32** |
| Full QB1+RB1+WR1+TE1 teams | **32 / 32** |

Sample artifact: `data/ops/nfl-season-engine-real-depth-sample-sf-la-20260804.json`

### Sample SF @ LA (week 1) roles

| Team | Role | Player |
| --- | --- | --- |
| SF | QB1 | Brock Purdy |
| SF | RB1 | Christian McCaffrey |
| SF | WR1 | Mike Evans |
| SF | TE1 | George Kittle |
| LA | QB1 | Matthew Stafford |
| LA | WR1 | Puka Nacua |

## Source + freshness

| Layer | Source |
| --- | --- |
| Upstream | [nflverse depth_charts release](https://github.com/nflverse/nflverse-data/releases/tag/depth_charts) `depth_charts_2026.parquet` |
| Upstream stamp | `timestamp.json` → `2026-08-03 06:36:43 EDT` |
| Snapshot dt | `2026-08-03T10:36:38Z` |
| Packaged artifact | `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json` |
| Regenerator | `scripts/nfl/package_season_engine_depth_2026.py` |

## Fallback chain

1. **`nfl_dp_depth_chart_weekly`** (preferred when populated)
2. **`nfl_dp_official_depth_charts`** (nflverse official table)
3. **Packaged nflverse skill snapshot** (`packaged_nflverse_depth_2026`)
4. **`demo_depth_chart`** (last resort / explicit `demo=true`)

Preseason bridge (Railway):

```bash
python -m data_platform_nfl.cli --seasons 2026 --ingest-official-depth-charts
python -m data_platform_nfl.cli --seasons 2026 --week 1 --materialize-weekly-from-official-depth
```

Launch hardening now also runs the official→weekly bridge after official ingest.

## Known gaps / limitations

- **Camp / preseason volatility** — depth charts move weekly; re-package or re-ingest after major cuts.
- **Rookies & FA landings** — present when nflverse lists them; mid-camp churn may lag.
- **WR/RB committees** — structure layer still applies equal/committee heuristics on top of identity order; shares are priors until usage weeks exist.
- **Efficiency** — still league / baseline priors when `nfl_player_projection_baselines` empty for 2026.
- **Some surprising landings** in the 2026-08-03 snapshot (e.g. FA moves) are taken as-is from nflverse — fantasy-usable current world, not a hand-curated board.

## Modeling layers

Unchanged from v1.9: team strength, game script, usage/depth volatility, red zone, coaching, injury reallocation. This cutover is **data/depth identity only**.

## UI

`/pro/nfl/*` status / game-boxes banners show `depth_source` + named-team coverage; star-out toggles use full 2026 names (dual-form matching still accepted).

## Tests

- `tests/test_nfl_season_engine_real_depth.py`
- Existing season-engine suite version assertions accept `real-depth`
