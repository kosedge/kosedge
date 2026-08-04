# NFL Season Engine — Real 2026 Schedule Cutover

**Date:** 2026-08-03  
**Engine version:** `nfl-season-engine-v1.9-real-2026`  
**Scope:** Data/schedule cutover only — modeling layers (calibration, injury, depth volatility, game-script, red-zone, coaching, survivor) unchanged from v1.8.

## Confirmation

| Item | Value |
| --- | --- |
| Default mode | `real` (not demo) |
| Schedule source (offline / DB-empty) | `packaged_wall_chart_2026` |
| Schedule source (when DB populated) | `nfl_dp_schedules` |
| REG game count | **272** (weeks 1–18, byes) |
| Demo opt-in | `demo=true` → round-robin (no byes) for unit tests |

Packaged artifact:

`services/model-service/src/services/nfl_season_engine/data/nfl_regular_schedule_2026.json`

Derived from `apps/web/lib/nfl-wall-chart-2026.schedule.json` (LAR → LA).

### Known 2026 checks

- Week 1: `ARI @ LAC`, `SF @ LA` (Rams home)
- Week 5 byes: `CAR`, `KC`
- Week 6 byes include `DET`, `CIN`, `MIA`, `MIN`

## Sample projection

Artifact: `data/ops/nfl-season-engine-real-2026-game-boxes-SF-at-LA-W1.json`

- Matchup: **SF @ LA**, Week 1 (`2026-W01-SF@LA`, `on_loaded_schedule`)
- Script (n=80): home WP ≈ 0.44, total ≈ 43.9, pace ≈ 63
- Named SF cores (Purdy / CMC) project; LA still on generic demo depth until DB depth charts load
- Survivor Week 5: byes `CAR`, `KC` excluded from ranked picks

## Roster / depth freshness

| Source | When used | Freshness |
| --- | --- | --- |
| `nfl_dp_depth_chart_weekly` | DB session + rows for season/week | `roster_as_of=season=…;as_of_week<=…` |
| `nfl_player_projection_baselines` | Efficiency overrides when present | same as_of_week window |
| Offline demo skill cores | DB depth empty / unreachable | `2025_offseason_approx` — 5 named teams (KC/BUF/PHI/SF/DET) + generics |

Resolver preference: DB schedule+depth → packaged schedule + DB depth when schedule empty → packaged schedule + demo depth when DB down.

## Gaps

1. **Depth charts / rookies:** Offline path still uses sparse demo cores; full 2026 depth + rookies require Railway `nfl_dp_depth_chart_weekly` (nflverse / NFL.com ingest) for season=2026.
2. **Kickoff times:** Packaged wall-chart has week/home/away only (no kickoff timestamps). Fair-lines still preferred in the UI picker when live rows exist.
3. **EPA strengths:** Offline packaged path keeps demo EPA-style bumps; DB path uses `_load_team_strength_priors`.
4. **Week 18:** Included in 272-game REG slate; confirm ops still treat postseason separately (engine is REG-only).

## Tests

- `tests/test_nfl_season_engine_real_schedule.py` — 272 games, known matchups, byes, `demo=true`, survivor bye exclusion, real game-boxes
- Existing demo-universe unit tests remain on `build_demo_universe` / `demo=true`

## Ops smoke (post-deploy)

```bash
# Status should show mode=real, ~272 games
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status" | jq '{engine_version,mode,schedule_source,schedule_game_count,roster_source,roster_as_of}'

# Real Week 1 matchup
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/game-boxes?home_team=LA&away_team=SF&week=1&season=2026&n_replicates=80"

# Survivor week 5 byes
curl -sS -X POST "$MODEL_SERVICE_URL/nfl/season-engine/survivor" \
  -H 'content-type: application/json' \
  -d '{"season":2026,"week":5,"n_sims":80,"already_used":[],"demo":false}'
```

BFF: `https://www.kosedge.com/api/nfl/season-engine/status` — UI should show real schedule banner (not amber demo).

## Railway + www smoke (2026-08-04 post-merge #86)

Live on `https://model-service-production-e253.up.railway.app` and BFF:

| Check | Result |
| --- | --- |
| Status | `nfl-season-engine-v1.9-real-2026`, `mode=real`, `schedule_source=packaged_wall_chart_2026`, `schedule_game_count=272` |
| Game-boxes | `SF @ LA` W1 → `game_id=2026-W01-SF@LA`, 14 players, total≈45.1 |
| Survivor W5 | byes `CAR`,`KC`; ranked picks exclude bye teams |
| www BFF status | same real mode / 272 games |

Roster still `demo_depth_chart` / `2025_offseason_approx` until Railway DB depth rows populate for 2026.
