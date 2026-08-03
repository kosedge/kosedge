# NFL Season Engine v1.3 — Deeper Player Usage

**Date:** 2026-08-03  
**Engine version before:** `nfl-season-engine-v1.2-injury-shocks`  
**Engine version after:** `nfl-season-engine-v1.3-deeper-usage`  
**Package:** `services/model-service/src/services/nfl_season_engine/`  
**Artifact JSON:** `data/ops/nfl-season-engine-deeper-usage-20260803.json`

## Goal

Make Layer 3 (player usage) more realistic and more sensitive to role, game
script, personnel / play mix, and injury presence — without breaking the
four-layer architecture or injury path shocks.

## What changed

### 1. Explicit usage-role taxonomy (`usage_roles.py`)

Inspectable labels on every skill role / usage row:

| Label | Typical meaning |
| --- | --- |
| `QB1` / `QB2` | Starter / backup |
| `RB1` / `RB2` / `RB_COMMITTEE` | Workhorse, committee partner, or near-even split |
| `WR1` / `WR2` / `WR3` / `WR_SLOT` | Alpha → depth / slot |
| `TE1` / `TE2` | Primary / secondary TE |
| `OTHER` | Residual / unranked |

Assigned in loaders via `annotate_roster_book` and re-applied inside usage /
injury paths. Exposed on game-box player rows as `usage_role` (+ `personnel`).

### 2. Base usage tables by role

`BASE_USAGE_BY_ROLE` supplies absolute snap / rush / target / route priors
when a loaded role is missing a field. Loaded demo/DB shares still win
(including **explicit zeros** after injury). Residual "other" bucket from
calibration is unchanged.

### 3. Game-script modifier matrix

`SCRIPT_USAGE_MATRIX` (lead / trail / neutral) — multipliers + snap deltas:

| Script | RB1 rush | WR1 targets | WR3 targets | Notes |
| --- | --- | --- | --- | --- |
| **trail** | ×0.88 | ×1.12 | ×0.94 | Pass-heavy; feed WR1/TE1 |
| **lead** | ×1.16 | ×0.96 | ×0.86 | Rush-heavy; fade WR3 |
| **neutral** | ×1.0 | ×1.0 | ×1.0 | Baseline |

Pass-rate bias from Layer 2 still shifts team pass/rush play mix; the matrix
shifts **who** gets the volume inside that mix.

### 4. Personnel / play-mix (light)

`infer_personnel_package(pass_rate, script)`:

- `pass_heavy` — trail **or** pass_rate ≥ 0.62 → 11-personnel tilt (WR routes up, TE snaps down)
- `rush_heavy` — lead **or** pass_rate ≤ 0.50 → 12/21 tilt (TE snaps up, WR3 down)
- `balanced` — otherwise

Tables live in `PERSONNEL_MIX_TABLE`.

### 5. Smarter injury reallocation

`injury_paths.reallocate_role_shares` now prefers
`INJURY_REALLOC_RULES` keyed by injured `usage_role`:

- **RB1 out** → RB2 primary rush sink (~58% of assignable), committee/RB3 residual; WR/TE catch spill
- **WR1 out** → WR2 > WR_SLOT > WR3; TE1 + RB1 spill
- **TE1 out** → TE2 primary TE sink; WR mix WR1>WR2>slot>WR3

Residual other fraction (`REALLOC_OTHER_FRACTION`) unchanged. Week ranges /
`out` / `limited` / `returning` availability math unchanged.

### 6. Diagnostics

- Player rows: `usage_role`, `personnel`
- Game-box notes: `usage_share_dump_home` / `usage_share_dump_away`
- `/nfl/season-engine/status`: `usage_roles.labels` + full rule tables

## Before / after examples (demo universe, same seeds)

### A. Healthy BUF @ KC (week 1, 300 reps, seed 2026)

Calibration sanity preserved (no Cook 100+ rush / Rice 9-catch nonsense):

| Player | Role | Carries / Targets | Production (mean) |
| --- | --- | --- | --- |
| J.Cook | RB1 | 13.7 carries | **57 rush yds**, 2.7 rec |
| R.Rice | WR1 | 8.5 targets | **5.2 rec / 55 yds** |
| I.Pacheco | RB1 | — | ~mid-50s rush (band) |
| P.Mahomes | QB1 | — | ~240–260 pass band |

### B. PHI script variants (120 draws, fixed pace 63)

| Script | RB1 carries | WR1 targets | WR3 targets | Pass rate |
| --- | --- | --- | --- | --- |
| lead | **20.3** | 7.1 | 1.8 | 0.48 |
| neutral | 15.3 | 9.0 | 2.9 | 0.58 |
| trail | **10.4** | **11.9** | 3.1 | 0.66 |

### C. SF injury — CMC out week 1 (200 reps, seed 9)

| Player | Healthy carries | CMC-out carries | Notes |
| --- | --- | --- | --- |
| C.McCaffrey (RB1) | 14.4 | **0.0** | zeroed |
| J.Mason (RB2) | 6.1 | **17.8** | differentiated RB2 sink |
| Home win prob | 0.627 | 0.586 | strength shock |

Week outside injury range remains unaffected (covered by tests).

## Tests

```bash
cd services/model-service
python3 -m pytest tests/test_nfl_season_engine_deeper_usage.py \
  tests/test_nfl_season_engine_injury_paths.py \
  tests/test_nfl_season_engine_calibration.py \
  tests/test_nfl_season_engine.py -q
```

Coverage:

- WR1 > WR2 > WR3 target shares (healthy)
- Trailing vs leading pass/rush shifts
- Injury zeros injured player; role-differentiated absorption
- Week outside range unaffected
- BUF@KC calibration sanity + version string

## Files touched

| Path | Change |
| --- | --- |
| `…/usage_roles.py` | **New** — taxonomy, base tables, script/personnel matrices, injury sink rules |
| `…/player_usage.py` | Role-aware allocation + diagnostics helpers |
| `…/injury_paths.py` | Role-aware reallocation (paths API unchanged) |
| `…/types.py` | `PlayerRole.usage_role`, `PlayerUsage.usage_role` / `personnel` |
| `…/loaders.py` | Annotate roles; richer demo WR3/TE2 depth |
| `…/game_query.py` | Expose roles + usage share dumps |
| `…/calibration.py` | `ENGINE_VERSION = nfl-season-engine-v1.3-deeper-usage` |
| `…/routes/nfl.py` | `/status` surfaces usage role rules |
| `tests/test_nfl_season_engine_deeper_usage.py` | **New** |
| `data/ops/nfl-season-engine-deeper-usage-20260803.md` | This report |
| `data/ops/nfl-season-engine-deeper-usage-20260803.json` | Numeric artifact |
| `data/ops/nfl-full-model-foundation-report.md` | Brief bump |

## Remaining weak spots

1. Role labels from depth order only — no true slot detection from route tree / alignment data
2. Personnel mix is coarse (3 buckets); no formation-play catalog
3. Script matrix is structural prior, not walk-forward fit
4. QB designed-rush still thin vs Allen/Hurts career shapes
5. Live injury report ingest still caller-supplied

## Deploy

Model-service `/nfl/season-engine/*` reads `DEFAULT_SEASON_ENGINE_VERSION`.
After merge to `deploy-vercel`, deploy Railway service `kosedge` (project
`joyful-clarity`) and smoke:

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status" | jq .engine_version
# Expect: nfl-season-engine-v1.3-deeper-usage
```
