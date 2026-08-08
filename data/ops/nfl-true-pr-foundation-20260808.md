# NFL True Power Rating Foundation — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Branch: `feat/nfl-true-pr-foundation` → `deploy-vercel`.

## Goal

Establish true 2026 power-rating construction on the **live** load path shared by Edge Board and the season engine:

1. No demo / placeholder influence on production team strength
2. Gradual prior → current blend (kill hard switch at `completed_reg >= 1`)
3. Full-strength PR vs current (availability-adjusted) PR as a clean split
4. Visible drivers + honest stub labels

## Construction formula (as implemented)

### Blend weights (per team, schedule-completed REG games)

| Team completed REG games | `w_current` | `w_prior` |
|--------------------------|-------------|-----------|
| 0 | 0.0 | 1.0 |
| 1–7 | `games / 8` (clamp 0–1) | `1 − w_current` |
| 8+ | 1.0 | 0.0 |

Implemented via existing `prior_current_blend_weight` + `blend_packages` in
`efficiency_backbone.py`, now called from live `_load_team_strength_priors`
(no longer test-only).

Schedule-completed games (not `games_in_window_5` alone) drive the weight so a
hydrated week grid cannot pretend a team has sample it has not earned.

### Components

- **Prior** = prior-season rolling efficiency backbone (latest week), else
  packaged 2025-derived backbone (`packaged_efficiency_backbone`).
- **Current** = current-season rolling (week-capped), only when that team has
  `completed_reg >= 1`. Missing current row → keep prior (team not dropped).
- **Blended package** = EPA / success / ST / pace fields blended, then mapped
  through `package_to_strength_indices` (v1.1 Off/Def/ST).
- **Uncertainty** = `uncertainty_from_games(team_completed_reg)`. Games 0–4 stay
  wide. League `completed_reg >= 1` does **not** tighten confidence by itself.

### Full-strength vs current

| Field | Meaning |
|-------|---------|
| `full_strength_*_index` | Intrinsic blended PR (no injury scars) |
| `offense_index` / `defense_index` | **Current** PR (contract consumed by sim) |
| `injury_delta_*` | `current − full_strength` |

At load time they are equal (`injury_status=structure_ready_zero`). Injury path
shocks (`apply_strength_shock`) and Edge Board nowcast multipliers mutate
**current** only and preserve full-strength.

### Stubs (labeled, not faked)

| Hook | Status |
|------|--------|
| QB premium | `stub_not_applied` (forced 0.0) |
| Continuity | `stub_not_applied` |
| True time-of-game SOS | `stub_not_applied` |

### Demo exclusion

Production load uses packaged real backbone + DB rolling only. Demo strength
bumps (`demo_epa_style_prior` / `_DEMO_STRENGTH_BUMPS`) remain `build_demo_universe`
only. Missing data → explicit `placeholder_league_avg` label, not silent demo fill.

## Shared core (Edge Board + season engine)

| Consumer | Path |
|----------|------|
| Edge Board / `simulate_nfl_game` | `_load_team_strength_priors` (**preferred**); matchup-pack EPA only if a team is missing from the blended book |
| Season engine | `load_universe_from_db` → same `_load_team_strength_priors` → `initialize_strengths` |
| Packaged offline | `build_packaged_real_universe` / packaged backbone (prior at 0 games) |

## Before / after at 0 / 1 / 4 / 8 games

| Games | Before (bug) | After (foundation) |
|------:|--------------|--------------------|
| 0 | Prior season / packaged (OK) | 100% prior; variance wide; drivers expose `w_current=0` |
| 1 | **Hard switch** to current-season 5g rolling | `w_current=1/8`; small move; not a recalibration |
| 4 | Current-dominated (post hard switch) | ~50/50 blend |
| 8+ | Current | 100% current (unchanged intent, honest path) |

## Smell tests (automated)

File: `services/model-service/tests/test_nfl_true_pr_foundation.py`

| # | Check | Result |
|---|-------|--------|
| 1 | Preseason hierarchy SEA ≫ ARI from prior | PASS |
| 2 | 1 game → `w_current=0.125`, small move | PASS |
| 3 | 4 games → 50/50 | PASS |
| 4 | 8+ → current-dominated | PASS |
| 5 | Full-strength ≠ current after injury shock | PASS |
| 6 | Smoke: packaged season engine / survivor / boxes (prior suite) | PASS (existing) |
| 7 | No demo labels on production strength path | PASS |

Also: `test_nfl_efficiency_backbone.py` + packaged EPA + prior-season loader — **26 passed** in local venv run.

## What is real vs stub

**Real**

- Prior/current blend on live loader
- Off / Def / ST (v1.1) drivers when sample present
- Uncertainty from current-season sample size
- Full-strength vs current structure + injury-path delta when shocks applied

**Stub / thin**

- QB premium, continuity, true time-of-game SOS
- Injury nowcast → current PR on Edge Board when `completed_reg >= 3` (existing early-season dampening unchanged); structure ready when dampened
- Rolling path still lacks week-aligned pass/run/early EPA (packaged has them)

## Remaining gaps (next passes — no scope creep)

1. Wire rolling pass/run/early-down EPA into live packages (parity with packaged v1.1)
2. Real QB premium identity layer
3. Continuity score (not silent zeros as if measured)
4. True adjusted SOS at time of game (past SOS vs future SOS — neither contaminates intrinsic PR)
5. Richer injury → defense delta on the live Edge Board path (offense shock is primary today)
6. Authenticated UI smoke of `/pro/nfl/model` + Edge Board after deploy

## Progress line

True PR foundation landed: live gradual blend + full-strength/current split + drivers/stubs; Edge Board and season engine share `_load_team_strength_priors`.
