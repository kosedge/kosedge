# Historical depth packs (Phase 3)

Preseason / W1 skill-depth snapshots used by
`nfl_season_engine.historical_replay`.

| Season | Cutoff rule |
|--------|-------------|
| ≤2024 | nflverse `week=1` + `game_type=REG` |
| ≥2025 | latest nflverse `dt` on/before Labor Day Monday |

Rebuild:

```bash
python scripts/nfl/package_historical_replay_depth.py --seasons 2019-2025
```
