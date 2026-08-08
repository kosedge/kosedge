# NFL team-strength ranking fix — after-action (2026-08-07)

## What users saw (symptoms)

Launch research / guest season layer produced absurd hierarchy:

- **Survivor Week 2 SEA@ARI** looked like a coin flip (~54% SEA / ~46% ARI) despite Seattle being clearly the stronger 2025 EPA club.
- **New England** sat near the **power-rank floor (~29–30)** with ~6.1 expected wins — treated like a rebuild bottom-feeder with no cause in recent EPA.
- Contender-era demo bumps kept **KC/BUF/PHI/SF/DET** artificially inflated while real 2025 season EPA told a different story (e.g. LA/SEA/NE/HOU strong; SF middling on EPA).

Live survivor/universe notes even admitted the fake book:

> Calibrated demo EPA-style priors with contender-tier bumps

## Root cause (confirmed with evidence)

1. Launch research used `--force-packaged`, which calls `build_packaged_real_universe()` in
   `services/model-service/src/services/nfl_season_engine/loaders.py`.
2. That function correctly loaded **real** packaged schedule + nflverse depth, but set:

   ```python
   strengths=demo.strengths  # from _DEMO_STRENGTH_BUMPS
   ```

3. Demo bumps explicitly crushed NE (`off: -0.09`, `def: -0.03`) and left SEA only mildly above ARI.
4. Railway prod tables `nfl_dp_team_rolling_features_weekly` / `_latest` were **empty (0 rows)**, so
   `_load_team_strength_priors()` in `tasks.py` could not supply real EPA on Railway either.

This was **not** a Survivor matchup-hack problem. The upstream strength book for “real” packaged mode was demo.

### BEFORE evidence (published 100k demo-strength bundle)

Source: `data/ops/nfl-preseason-sim-2026-20260807T183534Z/`
(pointer previously `data/ops/nfl-web-launch-bundle.json` → that bundle)

| Team | Demo strength (o/d) | Power rank (o+d) | Expected wins | W2 WP |
|------|---------------------|------------------|---------------|-------|
| SEA  | 1.022 / 1.034       | **18**           | 8.89          | 0.543 |
| ARI  | 0.998 / 0.956       | **24**           | 6.71          | 0.457 |
| NE   | 0.934 / 0.958       | **29**           | **6.12**      | —     |

W2 SEA@ARI gap: **+0.085** (coin-flip territory).

## Exact fix

### Packaged EPA prior artifact

Built from local Postgres:

- DSN: `postgresql://ryankos:postgres@127.0.0.1:5432/kosedge`
- Table: `nfl_dp_team_situational_weekly`
- Filter: `season=2025 AND source='nflverse'`
- Method: play-weighted season averages of `epa_per_play_offense` /
  `epa_per_play_defense_allowed` (+ seasonal avg pressure rates)
- Conversion: same contract as `tasks._epa_to_strength_indices` (Edge Board units)

Artifact path:

`services/model-service/src/services/nfl_season_engine/data/nfl_team_epa_priors_2026.json`

Rebuild script:

`scripts/nfl/build_packaged_epa_priors.py`

### Code changes

| File | Change |
|------|--------|
| `loaders.py` | `load_packaged_epa_priors()`; `build_packaged_real_universe` uses packaged EPA for all 32 teams (`source=packaged_epa_prior`); DB universe fills missing teams from packaged; **demo bumps only in `build_demo_universe`** |
| `tasks.py` | `_load_team_strength_priors` falls back to packaged priors when rolling features empty/partial |
| `team_strength.py` | Path-evolution tagging recognizes `packaged_epa_prior` |
| `__init__.py` | Export `load_packaged_epa_priors` |
| `tests/test_nfl_season_engine_packaged_epa.py` | Asserts not demo; SEA ≫ ARI; NE not bottom-tier |
| `run_launch_research_sims.py` | Summary includes `strength_source` / `strengths` notes |

No one-off matchup overrides. No ARI/SEA hardcodes.

## Before / after numbers

### Strength indices (2026 launch = 2025 EPA prior)

| Team | BEFORE demo o/d (c) | AFTER EPA o/d (c) | Rank before → after |
|------|---------------------|-------------------|---------------------|
| SEA  | 1.022 / 1.034 (2.056) | **1.040 / 1.117 (2.157)** | 18 → **2** |
| ARI  | 0.998 / 0.956 (1.954) | 0.974 / 0.911 (1.885) | 24 → **27** |
| NE   | 0.934 / 0.958 (1.892) | **1.068 / 1.082 (2.150)** | **29 → 3** |

Raw EPA (play-weighted 2025):

| Team | off EPA | def EPA allowed |
|------|---------|-----------------|
| SEA  | +0.045  | −0.124 (elite)  |
| ARI  | −0.019  | +0.088 (poor)   |
| NE   | +0.090  | −0.091 (strong both sides) |

### Full hierarchy highlights (AFTER composite rank)

**Top 8:** LA, SEA, NE, HOU, DEN, BUF, JAX, PHI  
**Middle:** DET/GB/IND/KC/CHI… through PIT/SF  
**Bottom 5:** WAS, LV, TEN, NYJ (plus ARI at 27)

(Real 2025 EPA — not nostalgia contender bumps. SF/KC look middling because their 2025 seasonal EPA was middling.)

### Survivor Week 2 SEA@ARI

| Bundle | SEA WP | ARI WP | Gap |
|--------|--------|--------|-----|
| BEFORE 100k demo-strength | 0.543 | 0.457 | +0.085 |
| AFTER 50k packaged EPA | **0.611** | **0.389** | **+0.222** |

### Expected season wins (team W/L paths)

| Team | BEFORE (100k) | AFTER (50k EPA) | Rank after |
|------|---------------|-----------------|------------|
| SEA  | 8.89 | **10.52** | 3 |
| ARI  | 6.71 | 6.71 | 27 |
| NE   | **6.12** | **10.56** | **2** |
| LA   | 8.29 | **10.80** | 1 |
| NYJ  | 8.05 | **4.92** | 32 |

Smell tests: SEA clearly above ARI on O+D and W2; NE near top (not floor); top/middle/bottom coherent with 2025 EPA.

## What was NOT changed

- **No matchup hacks** (no “set ARI to 20%” overrides).
- **Edge Board Week 1 path** still uses live `simulate_nfl_game` +
  `_load_team_strength_priors` / matchup pack. When Railway rolling tables are
  empty, that helper now falls back to the same packaged prior instead of
  silent league-average cold start — additive safety, not a board rewrite.
- Demo universe (`demo=True`) still uses `_DEMO_STRENGTH_BUMPS` for offline tests.

## Validation performed

1. **Unit tests:** `tests/test_nfl_season_engine_packaged_epa.py` — **5 passed**
   (plus related real-schedule/depth tests earlier in the session).
2. **10k validate:** `data/ops/nfl-season-engine-epa-validate-10k-20260807/`
   — W2 gap +0.222; NE expected wins ~10.6.
3. **50k + 1k player research (full successful run):**
   `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.12-survivor-planner-ux-Nteam50000-Nplayer1000-20260807T214449Z/`
   - Team W/L: 50,000 paths, `mean_wins_sum=272.0002`
   - Player full: 1,000 paths, 383 players
   - Survivor W1 derived from team matrix
4. **Published web bundle:** `data/ops/nfl-preseason-sim-2026-20260808T011817Z/`
5. **Pointer updated:** `data/ops/nfl-web-launch-bundle.json`

## Publish / PR status

- Branch: `fix/nfl-packaged-epa-priors` (from `deploy-vercel`)
- Web pointer identity: `nfl-season-engine-v1.12-survivor-planner-ux · N_team=50000 · 20260808T011817Z`
- PR: see GitHub URL after open (this note updated with URL in commit/PR body)
- HD mirror to `/Volumes/KosEdgeData/clean/nfl/research/` was attempted; sandbox blocked the external write — repo publish + pointer are authoritative for web.

## Remaining gaps

1. **Railway rolling features still empty** — packaged prior unblocks cold start, but prod should eventually repopulate `nfl_dp_team_rolling_features_weekly` / `_latest` for week-aligned 5g EPA (better than season-avg prior once games are played).
2. **N=50k vs prior N=100k** for team W/L — hierarchy/smell tests stable vs 10k validate; optional overnight 100k refresh later for tighter percentiles.
3. **SF/KC look “soft” vs public contender narrative** — this is intentional honesty to 2025 EPA, not a bug. Do not reintroduce demo contender bumps.

## Related ops notes

- Short fix note: `data/ops/nfl-packaged-epa-priors-fix-20260807.md`
- Research pointer: `data/ops/nfl-launch-research-sims-current.md`
- Web bundle pointer: `data/ops/nfl-web-launch-bundle.json`
