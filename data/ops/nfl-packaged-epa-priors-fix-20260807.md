# NFL packaged EPA priors fix — 2026-08-07

## Root cause

Launch research used `--force-packaged` → `build_packaged_real_universe()`.

That path loaded **real** packaged schedule + depth, but copied
`strengths=demo.strengths` from `_DEMO_STRENGTH_BUMPS`. Live notes said:

> Calibrated demo EPA-style priors with contender-tier bumps

Demo bumps crushed NE (`off: -0.09`, `def: -0.03` → power rank ~29) and left
SEA only mildly above ARI, producing Survivor Week 2 SEA@ARI coin-flips
(~54/46) despite 2025 season EPA showing SEA clearly superior.

Railway `nfl_dp_team_rolling_features_weekly` / `_latest` were empty (0 rows),
so `_load_team_strength_priors()` could not supply real EPA on prod either.

**Not** a matchup-hack problem — upstream strength book was fake in “real” mode.

## Fix

1. Built packaged prior artifact from local Postgres
   `nfl_dp_team_situational_weekly` (source=`nflverse`), season **2025**
   play-weighted averages of `epa_per_play_offense` /
   `epa_per_play_defense_allowed` (+ seasonal pressure rates).
2. Converted with the same `tasks._epa_to_strength_indices` contract used by
   live Edge Board / `simulate_nfl_game`.
3. `build_packaged_real_universe` now loads `packaged_epa_prior` for all 32
   teams — **never** `_DEMO_STRENGTH_BUMPS` in real mode.
4. `_load_team_strength_priors` fills missing teams from the packaged artifact
   when rolling features are empty/partial (Railway cold-start).
5. Demo universe (`demo=True`) still uses demo bumps for offline tests.

Artifact:
`services/model-service/src/services/nfl_season_engine/data/nfl_team_epa_priors_2026.json`

Rebuild:
`python scripts/nfl/build_packaged_epa_priors.py`

## Before / after (key teams)

### Strength indices (composite = offense + defense)

| Team | BEFORE (demo bumps) | AFTER (2025 EPA prior) | Power rank before → after |
|------|---------------------|------------------------|---------------------------|
| SEA  | o=1.022 d=1.034 c=2.056 | o=1.040 d=1.117 c=2.157 | 18 → **2** |
| ARI  | o=0.998 d=0.956 c=1.954 | o=0.974 d=0.911 c=1.885 | 24 → **27** |
| NE   | o=0.934 d=0.958 c=1.892 | o=1.068 d=1.082 c=2.150 | **29 → 3** |

### Survivor Week 2 SEA@ARI win probs

| | SEA | ARI | gap |
|--|-----|-----|-----|
| BEFORE (100k demo-strength research) | 0.543 | 0.457 | +0.085 |
| AFTER (10k EPA validate) | **0.611** | **0.389** | **+0.222** |

### Expected season wins (team W/L paths)

| Team | BEFORE (100k) | AFTER (10k validate) |
|------|---------------|----------------------|
| SEA  | 8.89 | **10.52** |
| ARI  | 6.71 | 6.73 |
| NE   | **6.12** | **10.57** |

Smell tests: SEA clearly above ARI on O+D and W2 WP; NE not dumped to floor;
top/middle/bottom coherent with 2025 EPA (LA/SEA/NE/HOU/DEN top; LV/TEN/NYJ bottom).

## Edge Board Week 1

Unchanged path: live `simulate_nfl_game` still prefers DB rolling EPA via
`_load_team_strength_priors`. When Railway rolling tables are empty, that
helper now falls back to the same packaged prior (instead of silent
league-average / record-only cold start). No matchup overrides added.

## Validation

- Pytest: `tests/test_nfl_season_engine_packaged_epa.py` (+ real schedule/depth)
- 10k validate: `data/ops/nfl-season-engine-epa-validate-10k-20260807/`
- Publish-scale re-run: 50k team + 1k player (see sibling launch dir +
  `nfl-web-launch-bundle.json` pointer after publish)

## Files changed

- `services/model-service/src/services/nfl_season_engine/loaders.py`
- `services/model-service/src/services/nfl_season_engine/team_strength.py`
- `services/model-service/src/services/nfl_season_engine/__init__.py`
- `services/model-service/src/services/nfl_season_engine/data/nfl_team_epa_priors_2026.json`
- `services/model-service/src/tasks.py` (`_load_team_strength_priors` fallback)
- `services/model-service/tests/test_nfl_season_engine_packaged_epa.py`
- `scripts/nfl/build_packaged_epa_priors.py`
- `scripts/nfl/run_launch_research_sims.py` (summary notes include strength_source)
- `data/ops/nfl-packaged-epa-priors-fix-20260807.md` (this note)

## Publish / PR status

- Branch: `fix/nfl-packaged-epa-priors` (from `deploy-vercel`)
- 50k+1k research: `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.12-survivor-planner-ux-Nteam50000-Nplayer1000-20260807T214449Z/`
- Web bundle: `data/ops/nfl-preseason-sim-2026-20260808T011817Z/`
- Pointer: `data/ops/nfl-web-launch-bundle.json` → N_team=50000 EPA priors
- Full after-action: `data/ops/nfl-team-strength-fix-after-action-20260807.md`
