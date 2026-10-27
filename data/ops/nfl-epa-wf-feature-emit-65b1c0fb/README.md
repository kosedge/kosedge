# 65b1c0fb — EPA walk-forward feature emit (2013–2022)

**`RESEARCH_DIAGNOSTIC` only. `CERT_CANDIDATE=0`.**  
NFL board **NO-GO**. Coming soon **ON**. No merge-to-prod / deploy / F2 / Odds API.  
Does **not** invent `epa_home_win_prob` / `epa_away_win_prob`.

Warehouse `nfl_dp_team_rolling_features_weekly` is not mounted here (`DATABASE_URL` unset) and is documented **2023–2026 only**. This emit backfills **2013–2022** from public nflverse PBP so t4422u / historical OOS can join features.

## Reproduce

```bash
pip install duckdb   # research VM only; not a production dependency
python3 data/ops/nfl-epa-wf-feature-emit-65b1c0fb/test_rolling.py
python3 data/ops/nfl-epa-wf-feature-emit-65b1c0fb/emit_rolling_2013_2022.py
```

PBP cache: `/tmp/nflverse_pbp/play_by_play_{2013..2022}.parquet`  
Source: `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet`

## PIT

For target week **W**, 3g/5g means use same-season team-weeks with `week < W` (bye weeks skip).  
Warehouse SQL includes `CURRENT ROW`; this CSV does **not**. A LEFT JOIN at `(season, week, team)` is pregame-safe.

Week 1 windows are empty (`EMPTY_WINDOW`). That is honest, not a silent zero.

## Join keys (t4422u / OOS)

| Key | Example |
| --- | --- |
| `season, week, home, away` | `2013, 1, STL, ARI` (historical OOS labels) |
| `oos_key` | `ARI@STL` |
| `join_game_id` | `2013_01_ARI_STL` |

PBP modern abbrs (`LA`/`LAC`/`LV`/`WAS`) are mapped onto OOS historical labels (`STL`≤2015, `SD`≤2016, `OAK`≤2019, `WSH`).

## Files

| File | Role |
| --- | --- |
| `games_join_2013_2022.csv` | one row per OOS game 2013–2022 |
| `team_week_rolling_pregame_2013_2022.csv` | team-week pregame features |
| `MANIFEST.json` | pins + sha256 |
| `ACCESS.json` | emit vs warehouse blocker |

## Not this

- Not CERT / CLEAR / graded results
- Not a remat of `nfl_dp_team_rolling_features_weekly`
- Not 2024+ holdout
- Not engine EPA win probs
- Not #642 forecast emit / not F2 / not #641
