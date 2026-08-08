# NFL Continuity Score (Prior Travel) — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Builds on merged **#140** (true PR blend), **#141** (player regression), **#142** (past SOS).

Branch: `feat/nfl-continuity-score` → `deploy-vercel`.

PR: _(filled after open)_

## Goal

Add a team **continuity score** that modulates **prior influence** in true PR
construction. Continuity is a **travel weight**, not a vibes rating and not a
new power scale.

- High continuity → prior counts more (same QB, coaches, returning production)
- Low continuity → prior counts less → lean on uncertainty / early current sample
- Missing inputs → **neutral contribution + approximate label** (never invent)

## Exact blend formula (no double-count with games/8)

```
w_current = clamp(completed_reg / 8, 0, 1)          # unchanged #140 curve
prior_travel = 0.35 + 0.65 × continuity_score      # TRAVEL_FLOOR=0.35
w_prior  = (1 − w_current) × prior_travel
w_anchor = (1 − w_current) × (1 − prior_travel)    # league-mean shrink
blended  = w_prior×prior + w_current×current + w_anchor×league_anchor
variance = uncertainty_from_games(g) + (1 − continuity_score)×0.24
```

| Games | `w_current` | Role of continuity |
|------:|------------:|--------------------|
| 0 | 0 | Scales starting prior weight; low continuity ≠ “last year locked” |
| 1–7 | `g/8` | Continuity scales residual prior mass only |
| 8+ | 1.0 | Current-dominated; continuity residual → 0 |

**Do not double-count:** continuity never replaces `games/8`.

## Continuity score (0–1)

| Factor | Weight | Direction |
|--------|-------:|-----------|
| QB returning / same starter | 0.40 | Strong positive if same; strong negative if new |
| HC / OC continuity | 0.25 | Both return → high; OC change → mid; HC or both → low |
| Returning production (skill yards + OL roster) | 0.25 | Positive with share returning |
| Major roster churn / FA overhaul | 0.10 | Negative when return share low / overhaul flagged |

**Bands:** `high` ≥ 0.72 · `mid` else · `low` ≤ 0.45

**Zero evidence** (all factors missing): `prior_travel = 1.0` (no invented mid discount).

## Wiring

| Step | Path |
|------|------|
| Pure math + loaders | `nfl_season_engine/continuity_score.py` |
| Blend travel | `efficiency_backbone.blend_packages(..., prior_travel_weight=…)` |
| Live load | `_load_team_strength_priors` after Past SOS, before blend |
| Drivers | `drivers.continuity` + `stubs.continuity=applied` · `qb_premium` stays stub |

## Data sources — real vs approximate

| Source | Role | Quality |
|--------|------|---------|
| `nfl_dp_player_game_stats` prior attempts | Prior primary passer | **Real** |
| `nfl_dp_official_depth_charts` QB depth_team=1 | Current QB1 | **Real** (packaged depth fallback) |
| `nfl_dp_rosters`  prior vs current | Returning production / churn / prior QB on roster | **Real** |
| Curated HC/OC flags (`CURATED_STAFF_BY_SEASON`) | Staff continuity | **Approximate** |
| Full coaching feed / OL snap shares | — | Thin / missing → neutral |

## Example teams (local DB, 2026-08-08)

| Continuity | Team | Score | Travel | Drivers (abbrev) |
|------------|------|------:|-------:|------------------|
| **High** | **DEN** | 0.95 | 0.97 | Same QB (Bo Nix); skill return ~1.00; roster return 0.73 |
| **High** | **DAL** | 0.92 | 0.95 | Same QB (Dak); high returning production |
| **High** | **KC** | 0.87 | 0.92 | Same QB (Mahomes); solid return shares |
| **Low** | **MIA** | 0.22 | 0.50 | New QB (Tua left); new HC+OC (approx); heavy churn |
| **Low** | **LV** | 0.26 | 0.52 | New QB (Geno→Cousins); new HC+OC (Kubiak, approx) |
| **Low** | **NYJ** | 0.34 | 0.57 | New QB (Fields→Geno); lower returning production |

Preseason hierarchy remains football-plausible after travel (continuity shrinks
toward league mean; it does not chaos-reorder SEA-type ≫ ARI-type priors).

## Explicit non-goal / next brief

**Full independent QB premium model is still next.**  
The QB *continuity factor* only answers “same starter vs new?” for prior
travel. It does **not** assign a talent premium, EPA bump, or KEI reprice.

Also out of scope here: 2026 projected SOS, opponent-tier UI, fantasy/CFB,
KEI/tag policy.

## Smell tests (automated)

File: `services/model-service/tests/test_nfl_continuity_score.py`
(+ true PR / SOS / backbone / player-regression suites)

| # | Check | Result |
|---|-------|--------|
| 1 | Same-QB / same-staff → high continuity, hard prior pull | PASS |
| 2 | New QB + new OC → low continuity, prior discounted, uncertainty up | PASS |
| 3 | Preseason hierarchy not chaos-reordered by continuity alone | PASS |
| 4 | Soft/hard Past SOS still visible on prior side | PASS |
| 5 | Full-strength injury path + player regression healthy | PASS |
| 6 | Packaged universe / live loader smoke | PASS |
| — | `games/8` curve preserved at travel=1.0 | PASS |

Local venv (2026-08-08): **40 passed** (continuity + true PR + SOS + backbone +
loader) and **11 passed** (player regression).

## Progress line

Continuity score ships as prior-travel modulation on the true-PR strength path;
games/8 blend, player finite production, and Past SOS remain intact; QB premium
still stubbed for the next brief.
