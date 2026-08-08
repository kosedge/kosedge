# NFL True PR Harden — Rookies Live + Season Finite — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Branch: `feat/nfl-true-pr-harden` → base `deploy-vercel`.

Depends on merged True PR stack: #140 blend, #141 player regression / finite,
#142 past SOS, #143 continuity, #144 QB premium, #145 future SOS. This pass
**activates and audits** — no new rating philosophy, no KEI/tag changes.

## Goal

1. **Rookie fields live** — `is_rookie` / `draft_round` (and `rookie_status`)
   populated on the depth → regression path so mean-shrink + wider CV fire.
2. **Season-level finite production audit** — beyond per-box scale-down, verify
   season-path named skill aggregates stay inside summed team script pools.

## What was inert vs now live

| Piece | Before (inert) | After (live) |
|-------|----------------|--------------|
| Packaged depth rows | Had `player_id` + names; **no** `is_rookie` / `draft_round` | Joined to packaged nflverse roster flags |
| DB weekly/official depth | Selected names only; rookie fields defaulted false | Selects `player_id`; joins `nfl_dp_rosters` (packaged fallback) |
| Regression knobs | `ROOKIE_MEAN_SHRINK` / wider CV wired but almost never triggered | Fire for `rookie_year == season` players |
| Season finite | Per-game `enforce_finite_team_production` only | Path audit + optional damp vs summed caps |

### Before / after (packaged 2026 path)

| Metric | Before enrichment | After |
|--------|-------------------|-------|
| `is_rookie` on skill depth roles | **0** | **38** |
| Rookies with known `draft_round` | 0 | 34 |
| Unclassified (no invent) | n/a | 3 depth ids missing roster join |
| Year-2 example (Ashton Jeanty) | would have been false anyway | **veteran** (`rookie_year=2025`) — correct |

Sample live rookies (post process priors):

| Player | Team | Draft | `experience_confidence` | CV mult | Drivers |
|--------|------|-------|-------------------------|---------|---------|
| Fernando Mendoza | LV | R1 | 0.45 | 1.55 | `rookie_wide_uncertainty`, R1 mild nudge |
| Jeremiyah Love | ARI | R1 | 0.45 | 1.55 | rookie + opportunity |
| Ty Simpson | LA | R1 | 0.45 | 1.55 | rookie wide uncertainty |
| Makai Lemon | PHI | R1 | 0.45 | 1.55 | rookie + R1 nudge |

**Classification rule (no invented capital)**

- `is_rookie` iff `rookie_year == season` (fallback `years_exp==0` or
  `entry_year==season` when `rookie_year` unset).
- `draft_round` from nflverse `draft_picks` / known `draft_number` slot map.
- Missing roster join → `rookie_status=unclassified`, `is_rookie=false`,
  `draft_round=null`.

Note: colloquial “2025 rookies” (Jeanty, Cam Ward, …) are **year-2** in
season=2026. Smell tests target the **2026 draft class**.

## Season finite method

1. Each game still runs `enforce_finite_team_production` (unchanged).
2. Along a season path, accumulate `team_production_caps` per team/game.
3. After the path, compare named skill season sums to summed caps.
4. If any field exceeds cap × **`SEASON_FINITE_TOLERANCE = 1.12`**, scale that
   team field down (never invent volume). Injury realloc stays in-team.

Diagnostics: `SeasonSimResult.diagnostics.season_finite_audit`.

### Evidence (packaged path, `n_sims=3`, seed=42)

| Check | Result |
|-------|--------|
| `season_finite_audit.ok` | **PASS** (`overflow_paths=0`) |
| path0 teams checked | 32 |
| path0 overflow / dampened fields | 0 / 0 |
| Tolerance | 1.12 |
| Unit overflow damp (synthetic) | **PASS** (`test_season_finite_audit_damps_overflow`) |
| Single-game finite still healthy | **PASS** |

Healthy paths usually sit inside per-game caps already; the season audit is the
safety net against silent 17-game inflation. Synthetic overflow tests prove damp
fires when needed.

## Smell tests

File: `services/model-service/tests/test_nfl_true_pr_harden.py`

| # | Check | Result |
|---|-------|--------|
| 1 | Known 2026 rookies `is_rookie` + wider bands | automated PASS |
| 2 | Hyped rookie does not dominate vet on mean | automated PASS |
| 3 | Season-sim skill vs team pools (tol 1.12) | automated PASS |
| 4 | Continuity / QB premium / past+future SOS / blend healthy | automated PASS |
| 5 | Game-box finite still works | automated PASS |

Also: `test_nfl_player_regression_finite_production.py` still green under
`ENGINE_VERSION = nfl-season-engine-v1.15-true-pr-harden`.

## Wiring

| Step | Module |
|------|--------|
| Packaged flags artifact | `nfl_season_engine/data/nfl_skill_rookie_flags_2026.json` |
| Join + classify | `loaders.enrich_depth_rows_with_rookie_flags` |
| DB rostres | `loaders._load_rookie_flags_from_db` → `nfl_dp_rosters` |
| Season audit | `player_regression.audit_season_finite_production` |
| Path hook | `season_sim.simulate_one_season_path` |
| Engine version | `nfl-season-engine-v1.15-true-pr-harden` |

## Remaining tolerance gaps

1. Season tol **1.12** is documented headroom over summed per-game caps —
   tighten only with more path evidence.
2. Compensatory picks make overall-pick → round slightly approximate when
   `draft_picks` gsis is missing (still never invents undrafted capital).
3. DB `nfl_dp_rosters` for season=2026 may lag packaged nflverse join offline;
   loaders prefer DB when present.
4. Full UI driver cards / fantasy desk — out of scope (next product pass).
5. KEI / tag policy — untouched.

## Explicit non-goals (honored)

- No new SOS product, QB premium redesign, fantasy desk, KEI/tag changes,
  or full UI driver cards.

## Progress line

True PR harden: live 2026-class rookie flags on depth→regression (38 packaged),
season-path finite audit with tol=1.12 + damp; smells green; stack #140–#145
unchanged in philosophy.
