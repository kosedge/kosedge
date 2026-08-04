# NFL Season Engine v1.7 — Red-Zone & Scoring-Specific Usage

**Date:** 2026-08-03  
**Engine version before:** `nfl-season-engine-v1.6-game-script`  
**Engine version after:** `nfl-season-engine-v1.7-red-zone`  
**Package:** `services/model-service/src/services/nfl_season_engine/`  
**New module:** `red_zone.py`  
**Artifact JSON:** `data/ops/nfl-season-engine-red-zone-20260803.json`

## Goal

Make touchdowns and red-zone work more realistic and more differentiated by
player role. TDs and red-zone are a first-class, inspectable part of the
usage → production path — without breaking depth-chart volatility, injury
shocks, game-script play-mix, survivor, or the four-layer hierarchy.

## How it works

```
team_strength → game_script → player_usage → [red_zone scoring usage] → production
```

1. **General usage (Layer 3)** still allocates snaps / routes / targets /
   carries from role tables + script matrix + personnel (unchanged).
2. **`red_zone.py`** estimates team RZ / I10 play volume (~14.5% of team
   plays; ~36% of those inside the 10), applies a **script-conditioned RZ
   pass rate**, then allocates:
   - I20 / I10 **carries** by scoring role
   - I20 / I10 **targets** + **routes** by scoring role
   - **TD opportunity share** (I10-weighted)
3. **Production (Layer 4)** keeps the **yards path** on general usage ×
   efficiency. **TD means** primarily = RZ opportunities × finish rates,
   plus a small non-RZ residual (`NON_RZ_TD_RESIDUAL = 18%`) of the legacy
   `usage × td_rate` poisson so explosive TDs are not zeroed. RZ volume is
   **not** added into yards (no double count).

### Role tables (documented)

| Scoring role | I20 carry | I10 carry | I20 target | I10 target |
| --- | ---: | ---: | ---: | ---: |
| RB1 | 0.56 | **0.66** | 0.09 | 0.08 |
| RB2 | 0.22 | 0.14 | 0.04 | 0.03 |
| RB_COMMITTEE | 0.36 | 0.32 | 0.06 | 0.05 |
| RB_GL (optional) | 0.42 | **0.52** | 0.03 | 0.04 |
| WR1 | 0.02 | 0.01 | 0.24 | **0.26** |
| WR2 | — | — | 0.15 | 0.13 |
| WR3 | — | — | 0.08 | **0.05** |
| TE1 | — | — | 0.18 | **0.24** |
| TE2 | — | — | 0.07 | 0.06 |

`RB_GL` is assigned only when a depth≥2 RB has loaded `red_zone_share` ≫
`rush_share`. Feature RB1 keeps the RB1 label (already elevated I10).

### Script interaction (RZ pass rate)

Leading → lower RZ pass / more RB I10 carries; trailing → higher RZ pass /
more WR1·TE1 I10 targets. Intensity × time-bucket scaling mirrors v1.6.

| Forced late script | RZ pass rate | RB1 I10 carries | RB1 TD opp share | WR1 I10 targets |
| --- | ---: | ---: | ---: | ---: |
| `large_lead` | **0.28** | **1.05** | **0.54** | 0.21 |
| `large_deficit` | **0.78** | 0.31 | 0.23 | **0.57** |

### Finish rates (primary TD path)

| Opportunity | Finish P(TD) |
| --- | ---: |
| Rush I20 (outside 10) | 0.12 |
| Rush I10 | 0.36 |
| Rec target I20 (outside 10) | 0.20 |
| Rec target I10 | 0.34 |

QB pass TDs ≈ team RZ receiving finishes (named + partial other-bucket
inflate) × QB attempt share + residual.

### Injury

Players with zeroed rush/target (availability 0) get zero RZ / TD
opportunity. Remaining backs absorb via existing injury realloc sinks on
general shares; RZ tables then allocate among eligible rushers.

## Before / after TD impact (key roles)

Analytical I10 sketch (neutral ~8 RZ plays, 52% RZ pass) vs v1.6 opaque
`usage × league td_rate`:

| Role | v1.6-style path | v1.7 I10 RZ sketch | Direction |
| --- | --- | --- | --- |
| RB1 rush TD | carries×0.027 (~0.40) | I10×0.66×0.36 (~0.31) + I20-out + residual | GL-concentrated; lead late ↑ |
| RB_COMMITTEE each | similar split of carries×rate | I10×0.32×0.36 (~0.15) each | Less concentrated than feature |
| WR1 rec TD | rec×0.055 (~0.30) | I10×0.26×0.34 (~0.12) + I20-out + residual | Elevated vs WR3 |
| TE1 rec TD | rec×0.055 (~0.23) | I10×0.24×0.34 (~0.11) + I20-out + residual | Elevated inside 10 |
| WR3 rec TD | rec×0.055 (thin volume) | I10×0.05×0.34 (~0.02) | Faded in scoring usage |
| QB1 pass TD | attempts×0.041 (~1.4) | team RZ rec finishes + residual | Tied to RZ targets, not yards |

Demo BUF@KC (250–300 reps, seed 2026) point estimates under v1.7:

| Player | Role | Pass/Rush/Rec TD | Yards |
| --- | --- | --- | --- |
| P.Mahomes | QB1 | pass TD **~1.25** | pass ~240 |
| J.Allen | QB1 | pass TD **~1.3** | pass ~230 |
| J.Cook | RB1 | rush TD **~0.51** | rush ~55 |
| I.Pacheco | RB1 | rush TD **~0.47** | rush ~59 |
| R.Rice | WR1 | rec TD **~0.32** | rec ~62 / 5.8 |
| T.Kelce | TE1 | rec TD **~0.27** | rec ~43 / 4.2 |

v1.6 artifact reference (same matchup family): Mahomes pass TD ~1.69, Cook
rush TD ~0.35, Rice rec TD ~0.30 — v1.7 shifts scoring toward RZ role
tables (RB GL / TE1 I10) while keeping yards on the general-usage path.

## Example box scores (BUF @ KC, demo)

See `nfl-season-engine-red-zone-20260803.json` for full distributions.
Diagnostics (`include_diagnostics=true`) expose:

- `red_zone.home/away.rz_pass_rate_mean` / `rz_run_rate_mean`
- `red_zone.players[]` with `rz_carries_i20/i10`, `rz_targets_i20/i10`,
  `td_opportunity_share`
- `scoring_usage.home/away` static role-table dump

## What stayed intact

- Depth-chart feature vs committee + weekly volatility
- Injury path shocks + role-aware realloc
- Game-script detail / intensity / play-mix (v1.6)
- Survivor W/L paths
- Four-layer hierarchy (RZ is a scoring-usage bridge, not a 5th layer)

## Remaining limitations

1. Still game-level analytic RZ volume — not drive-by-drive field position
2. No coaching tendencies / playbook-specific RZ dials
3. Sparse demo skill cores → residual other absorbs unnamed RZ volume
   (QB pass TD inflate partially recovers this)
4. Optional `RB_GL` heuristic is thin (loaded share ratio only)
5. Long/explosive non-RZ TDs are a fixed residual fraction, not a full
   chunked yardage model

## Tests

`services/model-service/tests/test_nfl_season_engine_red_zone.py`

- RB1 I10 carry ≫ WR; TE1/WR1 I10 targets ≫ WR3
- Leading late → more RZ run / RB TD share than trailing late
- Committee less concentrated than feature on I10 carries
- Injury zeros injured RZ/TD opportunities; RB2 absorbs on BUF
- BUF@KC Mahomes/Cook/Rice TDs in plausible bands + diagnostics present

## Smoke

Merged PR #82 → `deploy-vercel`; Railway `model-service`
(`brave-art` / `model-service-production-e253`) redeployed and smokes green:

- `GET /nfl/season-engine/status` → `nfl-season-engine-v1.7-red-zone` +
  `red_zone_scoring_usage` capability
- `GET .../game-boxes?...&include_diagnostics=true` → `diagnostics.red_zone` /
  `scoring_usage` with RZ pass rate + per-player I20/I10 opportunities

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status" | jq '{engine_version, capabilities}'
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/game-boxes?home_team=KC&away_team=BUF&week=1&demo=true&n_replicates=80&include_diagnostics=true" \
  | jq '{engine_version, red_zone: .diagnostics.red_zone.home, sample: .diagnostics.red_zone.players[0]}'
```
