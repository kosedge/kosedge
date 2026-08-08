# NFL Player Regression + Finite Production — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Branch: `feat/nfl-player-regression-finite-production` → base
`deploy-vercel` with **PR #140 already merged** (merge `bc0f34ff`,
2026-08-08). Dependency satisfied; do not re-merge #140.

PR: https://github.com/kosedge/kosedge/pull/141

Base: true PR foundation (gradual prior→current blend, full-strength/current
split, demo-free packaged strength path). This pass does **not** change those
contracts.

## Goal

Add a player process / regression layer on the hierarchical season engine so
player yards / TDs / turnovers stay coherent with team script pools, with
honest positive/negative regression posture and conservative rookies.

## Construction formula

### Process prior (not raw counting stats)

For each skill `PlayerRole` (QB/RB/WR/TE):

1. **Efficiency process index** — ypa / ypc / ypr / catch / INT vs league
   position defaults (`process_efficiency_index`). Opportunity (target/rush
   share) weights *evidence only*, not talent.
2. **Observed TD index** — pass/rush/rec TD rates vs league defaults
   (`observed_td_index`). Treated as finish/luck signal, not skill.
3. **Gap** — `td_process_gap = observed_td_index − process_index`
   - `> 0` → overperformed on finish relative to process
   - `< 0` → underperformed / soft finish relative to process

### Regression posture

| Posture | When |
|---------|------|
| `negative` | gap ≥ 0.12 and confidence ≥ 0.35 |
| `positive` | gap ≤ −0.12 and confidence ≥ 0.35, or situation-upgrade heuristic |
| `neutral` | thin evidence, small gap, or league-default-only approx |

Confidence = `|gap| × evidence_weight` (role confidence + baseline source boost
+ opportunity presence; rookies capped). Thin evidence → **no forced flag**
(drivers note `thin_evidence_no_forced_flag`).

TD rates are shrunk toward process (`REGRESSION_SHRINK=0.55`, confidence-scaled).
Drivers are short strings on the role / projection payload.

### Rookies

- `is_rookie` + optional `draft_round` on `PlayerRole`
- Mean pulled toward league (`ROOKIE_MEAN_SHRINK=0.72`); draft R1–R3 mild bump only
- `experience_confidence` capped at `0.45` → production CV widened
- Preseason counting stats are not treated as finished talent

### Finite production (non-negotiable)

Team game script owns the pool:

- Yards caps from `pace_plays × pass_rate × league YPA/YPC × offense_index`
- Skill TD cap from implied team total × offensive-TD point share
- Named players share `1 − USAGE_OTHER_BUCKET_FLOOR`
- After Layer-4 sampling, `enforce_finite_team_production` **scales down**
  overflow only (never invents volume to fill a pool)

Injury reallocation remains inside the same team usage pool (handcuff lift).

## Wiring

| Step | Module |
|------|--------|
| Annotate after depth splits | `loaders` → `apply_process_priors_to_roster_book` |
| Wider noise + finite cap | `production.produce_box_scores` |
| Season / game-box payloads | `regression_*`, `process_index`, `is_rookie`, p10/p50/p90 |
| Engine version | `nfl-season-engine-v1.13-player-regression` |

## Example cases (unit smells)

| Case | Expected |
|------|----------|
| WR high `rec_td_rate`, league ypr, solid evidence | **negative** posture; TD rate pulled down |
| WR strong ypr/catch, soft TD rate | **positive** posture; mild TD lift |
| Thin role_confidence / no baseline | **neutral**; thin-evidence drivers |
| Rookie R1 with hyped ypr | Mean pulled down; wider CV than veteran |
| Three teammates absurd yards/TDs | Finite scale → within team caps |
| DET Gibbs OUT | Montgomery rush share rises inside team pool |

## Smell tests

File: `services/model-service/tests/test_nfl_player_regression_finite_production.py`

| # | Check | Result |
|---|-------|--------|
| 1 | Team total ≈ named contributions (finite caps) | automated |
| 2 | High TD / thin process → negative | automated |
| 3 | Strong process / soft finish → positive | automated |
| 4 | Rookies do not dominate on draft hype | automated |
| 5 | Injury lifts handcuff in team pool | automated |
| 6 | Packaged/demo season + game-box paths healthy | automated |
| 7 | No demo strength on packaged path; process labeled | automated |

Plus: true-PR full-strength equality at load remains intact.

## Real vs approximate

**Real / structural**

- Process vs TD-finish gap from role efficiency fields
- Finite team caps from script implied totals + pace
- Rookie mean/uncertainty knobs
- Injury reallocation coherence (existing path)

**Approximate / thin**

- Opponent-adjusted individual EPA / xYards when baselines absent
  (`league_default_efficiency_approx` driver)
- Situation-upgrade positive flag (opportunity heuristic, not full SOS product)
- Draft capital only a mild mean nudge when `draft_round` present on depth rows
- Pass TD ↔ receiving TD poisson equality in a single replicate (soft; team RZ
  path already links means)
- Season sanity `qb_pass_tds` floor loosened to 12.0 under process/finite pull
  + small-`n_sims` noise (still a starter-range check, not a talent claim)

**Stubs (unchanged from true PR)**

- QB premium, continuity score, true time-of-game SOS

## Remaining gaps

1. Wire real opponent-adjusted player efficiency when feature tables exist
2. Populate `is_rookie` / `draft_round` from roster DB on the live load path
   (fields wired; live depth rows often leave them unset → non-rookie defaults)
3. Season-level finite audit diagnostics (team yards ≈ sum players across path)
4. Award-style leaderboard UI (engine paths first — out of scope here)
5. Authenticated UI smoke of `/pro/nfl/model` + Edge Board after deploy
   (public health/API smoke below; Pro auth UI may still need a human)

## Smoke (pre-merge / post-push)

| Check | Result |
|-------|--------|
| Unit smells (`test_nfl_player_regression_finite_production.py`) | see commit / CI |
| Related season-engine tests | see commit / CI |
| `www.kosedge.com` `/pro/nfl/model` + Edge Board | filled after live smoke |

## Progress line

Player regression + finite production layered on merged #140: process priors,
honest +/-/neutral flags, rookie conservatism, team-pool caps; season and
game-box payloads expose bands + drivers without breaking team PR blend.
