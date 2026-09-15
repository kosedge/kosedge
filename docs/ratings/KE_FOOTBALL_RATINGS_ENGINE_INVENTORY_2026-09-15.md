# KE Football Ratings Engine — inventory only (NFL + CFB)

**Date:** 2026-09-15  
**Track:** KE Football Ratings Engine audit / research. **Inventory only.**  
**Lock:** Ryan 2026-09-15 — CFB scoring [#562](https://github.com/kosedge/kosedge/pull/562) **REVISE** (margin improved, totals missed gate — do not loosen). NFL remediation is a separate track. Do not invent another scoring equation. No PFF. Boards stay dark.

This document **extends and reconciles** [#556](https://github.com/kosedge/kosedge/pull/556) (cross-sport inventory), [#558](https://github.com/kosedge/kosedge/pull/558) (NFL+CFB gap matrix + 2026 PBP path amendment), and CFB research [#555](https://github.com/kosedge/kosedge/pull/555) / [#559](https://github.com/kosedge/kosedge/pull/559) / [#560](https://github.com/kosedge/kosedge/pull/560) / [#562](https://github.com/kosedge/kosedge/pull/562). It is not a blank slate.

**No module named KE Football Ratings Engine exists.** There is no shared football feature library. NFL and CFB are separate stacks that happen to use similar words (efficiency, pace, explosiveness, power).

Companion: [`KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md`](./KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md) — gap matrix, data requirements, proposed layer. **STOP there for Ryan.**

---

## Classification legend

Same vocabulary as #556, plus the #558 two-axis rule (do not collapse “we have not built KE” into “we need to buy data”).

| Class                   | Meaning                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| **REAL_AND_VALIDATED**  | Owned (or contracted) measurement, wired to a consumer, with tests and/or graded ops evidence.                  |
| **REAL_UNVALIDATED**    | Real computation exists and is used or research-sealed, but is not a ratings SoT / not market-graded as KE.     |
| **PARTIAL**             | Real pieces exist; incomplete coverage, not fully wired, or split across stacks.                                |
| **PROXY**               | Derived from a correlated signal (vendor z-score, YPG, unit-grade heuristic) rather than the named measurement. |
| **PLACEHOLDER**         | UI copy, hook field, or empty desk; no computed rating.                                                         |
| **CONSTANT_OR_50_FILL** | League-average 50 / 1.0 / hardcoded constant used as a stand-in for missing measurement.                        |
| **DEAD_CODE**           | Computed or stored, but not consumed by the live ratings / compose / KEI path.                                  |
| **MISSING**             | No implementation found.                                                                                        |

**Vendor vs proprietary:** ESPN / Connelly SP+ is a real third-party rating. It is **not** KE. #556’s ~**28%** proprietary estimate is **unchanged** by later research: #559/#560 added research artifacts, not a live KE engine.

**Two worlds (required):** every CFB cell below is split **live compose / KEI** vs **research warehouse / #555–#562**. Collapsing them is the failure mode #556 already called out.

---

## 1. What changed since #556 / #558 (reconcile, do not reset)

| Claim in #556 / #558                                                 | After #555–#562                                                                                                           | Still true?                                      |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| No KE Ratings Engine module                                          | Unchanged                                                                                                                 | Yes                                              |
| NFL is the only live owned play-level efficiency spine               | Unchanged. Boards now **dark** (#561); spine still exists                                                                 | Yes                                              |
| CFB live = final-2025 SP+ + synthetic success / explosiveness / pace | Unchanged on compose                                                                                                      | Yes                                              |
| CFB 2026 form = NEED_EXTERNAL / CFBD-blocked                         | **Superseded.** SDV 2026 PBP is on the versioned current path (#558). #559 built W−1 raw team-game metrics (research)     | Data available; **not** live KE                  |
| CFB opponent-adj KE = NEED_EXTERNAL                                  | **Wrong axis** (#558). #560 **merged**: research joint-ridge O/D EPA, 2025 holdout ADVANCE, `production_promote=false`    | Research REAL_UNVALIDATED; live still vendor SP+ |
| Warehouse 4-iter EPA adj unused                                      | Still unused by compose. #560 is a **second** research estimator, not a replacement of live SP+                           | Yes                                              |
| First recommended build = 2026 W−1 raw metrics                       | **Done in research** (#559). Closed eligibility later **84** games after delayed-game PBP fail-close (#560)               | Do not rebuild as if missing                     |
| Scoring conversion next                                              | #562 **REVISE**. Margin MAE 13.05 vs 14.26 (−8.5%). Total MAE 14.15 vs 13.68 (**+3.4% worse**). Locked rule required both | **Do not invent a new equation**                 |
| ~28% proprietary KE                                                  | Unchanged. Research EPA ≠ implemented KE Ratings                                                                          | Yes                                              |
| Boards / KEI                                                         | #561 Coming soon. Public flags false                                                                                      | Stay dark                                        |

NFL numbers in #556 remain the live-path description. This inventory re-traces them and flags remediation as **out of scope**.

---

## 2. Architecture that actually exists (not the target)

Ryan’s target framing (visible for review; **not implemented as one spine**):

```text
data truth → football measurement → opponent adjustment → team strength
         → matchup interaction → scoring projection → market comparison
```

What ships today:

```text
NFL live:
  nflverse PBP → situational / rolling / ST KAV / KAV
    → efficiency_backbone v1.1 → TeamStrengthState
    → expected_team_points → Power desk / True PR / season sim / (dark) Edge Board

CFB live:
  Final-2025 SP+ scrape → 0–100 z-map + synthetic success/explosiveness
    → compose (roster + QB + units + coaching + HFA)
    → expected_team_points (matchup^response × pace proxy × ST 50-nudge)
    → KEI / (dark) Edge Board

CFB research (not compose):
  SDV PBP 2014–2025 + 2026 current → raw team-game (#555/#559)
    → #560 opp-adj O/D EPA (ADVANCE)
    → #562 points/margin/total (REVISE — totals failed)
```

A working (or parked) board is not a finished ratings engine. A sealed EPA MAE is not a spread. A failed totals conversion is not permission to write a new scoring equation.

---

## 3. NFL inventory

**North star:** `data/ops/nfl-model-vision.md`.  
**Spine:** `efficiency_backbone` **v1.1** (`EFFICIENCY_BACKBONE_VERSION`).  
**Stamp / ops:** `data/ops/nfl-efficiency-backbone-v1.1-20260808.md`.  
**Public boards:** parked (#561). Internal path still computes.

### 3.1 Canonical live trace

```text
nflverse PBP
  → nfl_dp_play_by_play
  → nfl_dp_team_situational_weekly     (EPA, success, explosive pass ≥20 yd, RZ, pressure, pace)
  → nfl_dp_team_rolling_features_weekly (3g/5g trailing)
  → nfl_dp_matchup_features_weekly     (home/away/diff 5g + KAV + ST KAV)
  → efficiency_backbone.TeamEfficiencyPackage
  → package_to_strength_indices / TeamStrengthState
  → expected_team_points
       ├─ power_ratings_desk (Method B Model PR)
       ├─ true_pr_product
       ├─ nfl_simulator + handicapping framework
       └─ (dark) Edge Board / /pro/power-ratings/nfl / /pro/nfl/model
```

Cold start: `scripts/nfl/build_packaged_efficiency_backbone.py` → `nfl_team_efficiency_backbone_2026.json`.

### 3.2 Component cards

#### KE Offensive Efficiency — **REAL_AND_VALIDATED** (live)

| Field               | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Raw source**      | nflverse PBP → `nfl_dp_team_situational_weekly` / rolling 5g. Packaged prior = 2025 REG.                                                                                                                                                                                                                                                                                                                                                               |
| **Exact formula**   | Base: `offense_index = clamp(1.0 + off_epa*0.75 + (pressure_gen − pressure_allowed)*0.18, 0.82, 1.22)`. Soft additives (shrunk by `1/variance`): success vs 0.44 (`_W_SUCCESS=0.12`), explosive pass vs 0.085 (`_W_EXPLOSIVE=0.08`), RZ TD vs 0.55 (`_W_RZ=0.06`), pass/run/early-down EPA (`0.05` / `0.035` / `0.04`), ST bleed `0.5 * 0.065 * (st_index−1)`. Prior/current blend: `w_current = clamp(games/8, 0, 1)`. Games 0–2 labeled prior-heavy. |
| **Coverage**        | Rolling cited 2023–2026 (2,286 rows). Packaged 2026 ← 2025.                                                                                                                                                                                                                                                                                                                                                                                            |
| **PIT**             | Current season week-capped; completed games gated by schedule scores. Matchup/KAV join week W−1.                                                                                                                                                                                                                                                                                                                                                       |
| **Cadence**         | Weekly situational ingest; rematerialize rolling; rebuild packaged at least once per offseason.                                                                                                                                                                                                                                                                                                                                                        |
| **Persistence**     | Postgres `nfl_dp_*`; JSON `nfl_team_efficiency_backbone_2026.json`.                                                                                                                                                                                                                                                                                                                                                                                    |
| **Model consumers** | `_load_team_strength_priors`, season engine, simulator, Power desk, True PR.                                                                                                                                                                                                                                                                                                                                                                           |
| **UI consumers**    | `/pro/power-ratings/nfl`, `/pro/nfl/model`, Edge Board O/D chips — **public dark**.                                                                                                                                                                                                                                                                                                                                                                    |
| **Validation**      | `tests/test_nfl_efficiency_backbone.py`, ops v1 / v1.1 hierarchy smell (SEA ≫ ARI; NE not crushed).                                                                                                                                                                                                                                                                                                                                                    |
| **Not KE-complete** | League-mean center is not full SOS. Soft additives are football context on top of EPA, not a second book. Remediation track is separate.                                                                                                                                                                                                                                                                                                               |

#### KE Defensive Efficiency — **REAL_AND_VALIDATED** (live)

| Field                                                  | Evidence                                                                                                                                                                                     |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Raw source**                                         | Same situational table; defense-allowed EPA / success / explosive / RZ / pressure generated.                                                                                                 |
| **Exact formula**                                      | `defense_index = clamp(1.0 + (−def_epa_allowed)*0.90 + pressure_delta*0.14, 0.82, 1.24)` + inverted soft additives + `0.5` ST bleed.                                                         |
| **Coverage / PIT / cadence / persistence / consumers** | Same spine as offense.                                                                                                                                                                       |
| **Gaps (ops v1.1)**                                    | Defense-allowed RZ still soft/partial vs offense RZ. Rolling path still lacks week-aligned pass/run/early-down EPA (packaged cold-start has splits; live rolling uses overall 5g + ST join). |

#### KE Special Teams Efficiency — **REAL_UNVALIDATED**

| Field             | Evidence                                                                                                                                                                                                                                                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Raw source**    | `nfl_dp_team_st_kav_weekly` via `scripts/nfl/build_st_kav_weekly.py` (builder cites 2013–2025).                                                                                                                                                                                   |
| **Exact formula** | `st_index = clamp(1.0 + st_epa*0.55, 0.85, 1.15)`. Missing ST → `st_index=1.0` labeled `neutral_hook` (**CONSTANT_OR_50_FILL** on the hook, not a 50-scale). Play counts for thin-sample labels are approximated (~8/game × games), not exact PBP joins (ops v1.1 remaining gap). |
| **PIT / cadence** | Built from PBP; weekly rematerialize.                                                                                                                                                                                                                                             |
| **Consumers**     | Soft bleed into O/D indices; desk labels ST **approximate**.                                                                                                                                                                                                                      |
| **UI**            | Power / True PR drivers. Not a standalone ST ranking product.                                                                                                                                                                                                                     |

#### KE Pace — **PARTIAL**

| Field                   | Evidence                                                                                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Measured (backbone)** | `pace = (off_plays/games) / 62.0`, clamp 0.88–1.12. League anchor `_LEAGUE_PLAYS_PER_GAME=62`.                                                                      |
| **Also present**        | `game_script.py` coaching overlays; `team_pace_factor` in player-production ingest (`offensive_plays/64`, clamp 0.75–1.25) — **player spine**, not Layer-1 ratings. |
| **PROXY**               | Static UI pack `apps/web/lib/nfl-structural-pace-2026.ts` for Edge Board bullets.                                                                                   |
| **Class**               | PARTIAL = measured plays/game on the strength package + a separate UI proxy. Do not call the UI pack “KE Pace.”                                                     |

#### KE Explosiveness — **PARTIAL**

| Field                 | Evidence                                                                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Live backbone**     | Pass explosive: situational ingest `passing_yards >= 20`. Additive vs league 0.085. Rush explosive **not split** (ops v1). Missing → 0.085, not 50. |
| **KAV (separate)**    | `yards_gained >= 12` (`EXPLOSIVE_YARDS=12`). Game-level, **not** Layer-1 PR.                                                                        |
| **Tendency profiles** | Explosive run ≥10, pass ≥20 (`test_team_situational_tendencies_explosive_and_sack_rate`). Another definition.                                       |
| **Class**             | PARTIAL. Three yard thresholds exist. Named KE explosiveness (pass **and** rush, one definition, opponent-adjusted) is **MISSING**.                 |

#### KE Finishing Drives — **PARTIAL**

| Field             | Evidence                                                                                     |
| ----------------- | -------------------------------------------------------------------------------------------- |
| **Live**          | `red_zone_td_rate` vs 0.55, weight 0.06. Matchup `diff_red_zone_td_rate_5g` in simulator.    |
| **Not finishing** | Season-engine `red_zone.py` is **player TD role shares** (PROXY relative to team finishing). |
| **Missing**       | Scoring-opportunity rate, points per opportunity, drive-finish rate as a ratings feature.    |

#### KE Havoc / Disruption — **PROXY** (named metric **MISSING**)

| Field             | Evidence                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **What exists**   | Pressure generated/allowed inside `epa_to_strength_indices`; sack rate in tendency profiles; OL `protection_index` injury heuristic. |
| **What does not** | TFL + INT + FF + PBU havoc rate. Do not relabel pressure as KE Havoc.                                                                |

#### EPA / PPA — **REAL_AND_VALIDATED** (EPA) / **MISSING** (PPA, optional)

nflverse `AVG(epa)` / `AVG(success)` in data-platform ingest. No NFL PPA. PPA is **not** required (#558).

#### Opponent adjustment — **PARTIAL** (three stacks; do not double-count)

| Stack              | Class            | Formula / note                                                                                                                                |
| ------------------ | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| League-mean center | PROXY            | `opponent_adjust_epa(raw, league) = raw − league` in backbone                                                                                 |
| Past SOS           | REAL_UNVALIDATED | `adj_off = raw_off + 0.70*(league_def − mean_opp_def)` (`_SOS_DAMPEN=0.70`). Prior side; W−1 opp book. Tests: `test_nfl_adjusted_sos_past.py` |
| KAV iterative      | REAL_UNVALIDATED | 12-iter EPA/success/explosive; `kav_pct = (adj_epa − league_mean) / 0.15`. **Not** Layer-1 PR (`power_ratings_desk.py` forbids double-count)  |
| Projected 2026 SOS | REAL_UNVALIDATED | Outlook only; does not rewrite intrinsic PR                                                                                                   |
| External DVOA hook | PLACEHOLDER      | Only if caller passes values                                                                                                                  |

#### Strength of schedule — **REAL_UNVALIDATED**

Past SOS as above. Not win-pct SOS (`not_opponent_win_pct: true`). Not the Layer-1 identity of “good.”

#### Power ratings / team strength — **REAL_AND_VALIDATED** (live compute; public dark)

| Field                 | Evidence                                                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Team strength**     | `TeamStrengthState` from backbone indices. `expected_team_points`: `LEAGUE_TEAM_PPG * (1 + response*(off/def − 1))` + HFA ~1.05 + tiny FG-environment.                    |
| **Power (Method B)**  | Expected margin vs synthetic average opponent, then `zero_center`. Tuesday shrink `PR_pub = (1−α)*PR_prior + α*PR_data` (`ALPHA_BY_WEEK` 0.12→0.80). Ryan Adj defaults 0. |
| **True PR**           | `intrinsic_pr = 0.5*(full_strength_off + full_strength_def)`. Display.                                                                                                    |
| **Persistence**       | `scripts/nfl/tuesday_power_ratings_update.py` → `data/ops/nfl-power-ratings-desk/latest.json`.                                                                            |
| **UI**                | `/pro/power-ratings/nfl` — parked.                                                                                                                                        |
| **In-path evolution** | Simulated-season mean-revert is **PLACEHOLDER** relative to measured ratings (explicit in `team_strength.py`).                                                            |

#### Player / QB / continuity — **PROXY** (not KE player ratings)

`qb_talent_factor_from_prior_ypg` / skill YPG multipliers. QB premium layer exists (`qb_premium.py`, scale 0.058, cap 0.070) — REAL_UNVALIDATED team-level; ops v1.1 still notes hook often 0.0. Continuity score is curated 2026 staff flags — REAL_UNVALIDATED, not EPA.

#### NFL fills (do not conflate with CFB 50s)

| Location                         | Value                              | Class                              |
| -------------------------------- | ---------------------------------- | ---------------------------------- |
| Missing ST                       | `st_index=1.0` `neutral_hook`      | CONSTANT_OR_50_FILL                |
| Missing explosive / success / RZ | 0.085 / 0.44 / 0.55                | CONSTANT_OR_50_FILL (rate anchors) |
| No strength artifact             | O/D = 1.0 `placeholder_league_avg` | CONSTANT_OR_50_FILL (index scale)  |
| Demo strength bumps              | Demo-only                          | DEAD_CODE for real mode            |

---

## 4. CFB inventory

**Engine stamp (live):** `cfb-season-engine-v0.15-power-sot`.  
**Honesty docs:** `data/ops/cfb-efficiency-backbone-20260804.md`, `docs/CFB_CH2_EFF_PACK_AUDIT.md`, `docs/CFB_CH2_EFF_CARRY_SCORECARD.md`, `docs/CFB_TOTALS_HOT_AUDIT.md`.  
**Public boards:** parked (#561). Compose still computes.

### 4.1 Live compose / KEI trace (unchanged by #555–#562)

```text
Final-2025 SP+ (cfbupdate / ESPN story / optional CFBD /ratings/sp)
  → scripts/cfb/package_efficiency_2025_carry.py
  → cfb_efficiency_snapshot_2025_carry_2026.json
       as_of=2026-08-31 · 147 teams · 141 mapped SP+ · 6 league_average_fill
  → efficiency.build_efficiency_profile + optional in_season_update
  → roster + qb_situation + position_groups + HFA + coaching
  → compose_team_projection → expected_team_points → project_game
  → apply_cfb_kei → (dark) Edge Board / /pro/cfb/project-game
```

`pbp: not_used` in the snapshot source block.

### 4.2 Research traces (not compose)

**Warehouse (2014–2025, leakage-tested, `used_in_spread: false`):**

```text
HD PBP 2014–2025 (canonical `/Volumes/KosEdgeData/raw/cfb/pbp/` — do not overwrite)
  → efficiency_adj.aggregate_team_games (garbage weights)
  → iterative_adjust (EPA only, 4 iters, shrink n/(n+80))
  → week_snapshots (week W uses week < W) + season finals
  → cfb_preseason_prior_2026.json (research_prior on project-game only)
```

**#555 / #559 raw metrics (unadjusted):**

```text
SDV PBP → owned_metrics.team_game_raw_metrics
  success (EPA_success = EPA>0), standard 50/70/100 SR,
  EPA/play, pace / competitive pace, explosiveness (+ pass/rush),
  down splits, scoring opportunities / PPO / finishing, field position
  opponent_adjusted = false
```

**#560 opp-adj EPA (merged, ADVANCE, not KE Ratings):**

```text
y = μ + h·home + off_i + def_j
garbage-weighted EPA/play; joint ridge λ=40, n0=4, decay=0.75, λ_fcs=4λ, 12 iters
2025 holdout MAE 0.1673 vs unadj 0.1911 / blend 0.1837
production_promote = false
```

**#562 scoring (open, REVISE — not a ratings component):**

```text
points_i = 25.73 + 0.787 · (epa_i · exp_plays) + 5.87 · home_i
margin OK vs prior-points blend; total worse than train league mean
Do not retune. Do not invent a replacement equation in this track.
```

### 4.3 Live efficiency formulas (vendor → 0–100) — **not measured football**

From `scripts/cfb/package_efficiency_2025_carry.py`:

```text
z_off = (sp_offense − μ_off) / σ_off
z_def = (μ_def − sp_defense) / σ_def          # inverted so higher = better
off_eff_raw = clamp(50 + 18*z_off, 5, 95)
def_eff_raw = clamp(50 + 18*z_def, 5, 95)
success_*_raw = clamp(50 + 16*(0.85*z_*), 5, 95)          # PROXY
expl_raw = clamp(50 + 17*max(-1.5, z_off − 0.35*max(0, −z_off)), 5, 95)  # PROXY
eff' = 50 + 0.85*(eff_raw − 50)               # EFF_CARRY_SHRINK
```

`success_*` and `explosiveness` are documented **SP+-correlated proxies, not PBP**.

### 4.4 Component cards — live vs research

#### KE Offensive Efficiency

| Axis            | Live compose                                                                                                                  | Research                                                                                                                                                         |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Class**       | **PARTIAL** (vendor SP+ carry, real opponent-adjusted _source_, not owned, stale to final-2025)                               | Warehouse 4-iter EPA: **REAL_UNVALIDATED** / unused. #560 joint-ridge EPA: **REAL_UNVALIDATED** (holdout-sealed as _next-game EPA_, not as KE Ratings or points) |
| **Raw source**  | cfbupdate HTML (default) or CFBD `/ratings/sp?year=2025`                                                                      | SportsDataverse `espn_cfb_pbp` `EPA` (name unchanged)                                                                                                            |
| **Formula**     | z-map + 0.85 shrink above                                                                                                     | #560: `y = μ + h·home + off + def`; ridge toward decayed prior                                                                                                   |
| **Coverage**    | One final-2025 table; 141/147 mapped                                                                                          | Hist restore 2014–2025, 10,297 games; 2026 closed eligible **84**                                                                                                |
| **PIT**         | **Not** in-season PIT. `in_season_update` moves 0–100 from **margin residuals** (`RESIDUAL_TO_EFF=0.35`) — still proxy-linked | Week W uses `week < W`. Delayed+score+incomplete PBP **excluded** (`401868140`)                                                                                  |
| **Cadence**     | Manual rematerialize of snapshot                                                                                              | Research runners; HD lake not rewritten                                                                                                                          |
| **Persistence** | `cfb_efficiency_snapshot_2025_carry_2026.json`                                                                                | Research JSON under `data/ops/cfb-research-opp-adj-epa-20260915/`; warehouse parquets on HD (often unmounted)                                                    |
| **Consumers**   | Compose `WEIGHT_OFF_EFF=0.34` + `EFF_OFF_INDEX_BLEND=0.12`                                                                    | **None live.** `used_in_spread: false`. `NOT_KE_RATINGS=true`                                                                                                    |
| **UI**          | `/pro/cfb/project-game` Off chip                                                                                              | None                                                                                                                                                             |

Official FBS missing SP+ **hard-fails** (good). Six snapshot rows are explicit `league_average_fill` = 50.

#### KE Defensive Efficiency

Same dual stack as offense. Live `WEIGHT_DEF_EFF=0.36` + `EFF_DEF_INDEX_BLEND=0.12`. #560 `def` is EPA allowed (lower better), FBS-centered at 0. Do not convert `h≈0.244` to a spread (#560 audit).

#### KE Special Teams Efficiency

| Axis             | Live                                                                                                                                                                                                                    | Research                                                                                               |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Class**        | **PROXY** + **CONSTANT_OR_50_FILL**                                                                                                                                                                                     | **PARTIAL** data / **NEEDS_VALIDATION** (#558)                                                         |
| **What exists**  | Unit grade `special_teams` default 50. Compose nudge `st_nudge = 0.015 * ((st_h+st_a)/2 − 50)` (`SPECIAL_TEAMS_TOTAL_SCALE`). Packaged `sp_special_teams` is **unused** in compose (**DEAD_CODE** relative to scoring). | 2026 raw has kick/punt/FG `type.text` + ~83 ST columns. Completeness not certified. No ST EPA product. |
| **Not measured** | No punt/FG/return EPA on the live path.                                                                                                                                                                                 | Do not call flags “KE ST” until a definition + completeness audit exists.                              |

#### KE Pace

| Axis        | Live                                                                                                                                                           | Research                                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Class**   | **PROXY**                                                                                                                                                      | **REAL_UNVALIDATED** (raw, unadjusted)                                                                           |
| **Formula** | `pace = clamp(1.0 + (skill − front_seven)/200, 0.85, 1.20)` then `+ (explosiveness−50)/400`. Totals audit: mean pace **0.996**, expl ~**49.8** — not the Over. | #555: scrimmage plays / offense game; competitive pace `\|pos_score_diff\| < 16`. #559 materialized on 2026 W−1. |
| **UI**      | `/pro/cfb/tempo` **PLACEHOLDER** (“while dedicated tempo feeds finish join”)                                                                                   | None                                                                                                             |

**Do not represent live pace as measured tempo.**

#### KE Explosiveness — **flag: synthetic on live path**

| Axis         | Live                                                                                                                                         | Research                                                                                                                                   |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Class**    | **PROXY** (synthetic)                                                                                                                        | **REAL_UNVALIDATED** raw; warehouse explosive **DEAD_CODE** at adj                                                                         |
| **Formula**  | `expl_raw = 50 + 17*max(-1.5, z_off − 0.35*max(0, −z_off))` then shrink 0.85. **A function of SP+ offense z**, not play-level iso-explosion. | `EPA ≥ 1.0` **or** `statYardage ≥ 15`; pass/rush splits. Kos knobs, not a vendor iso-explosion.                                            |
| **Live use** | Tiny pace nudge only. `success_*` are **driver metadata** — not in `expected_team_points`.                                                   | #559 columns present; `opponent_adjusted=false`. Warehouse stores `off_explosive_rate` then **drops it** at `iterative_adjust` (EPA only). |

This is the previously discovered explosiveness proxy. **It is not measured football efficiency.**

#### KE Finishing Drives

| Axis      | Live                             | Research                                                                                                                                                                                                                                                            |
| --------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Class** | **MISSING** / **DEAD_CODE**      | **REAL_UNVALIDATED** raw                                                                                                                                                                                                                                            |
| **Live**  | No PPO / finish rate in compose. | Opportunity = drive reaches `yardsToEndzone ≤ 40` or `rz_play`. Finish = opportunity with `points_on_drive > 0`. Points from `type.text` heuristic (TD 6, XP 1, FG 3, safety 2) — **not** official drive-result points. Warehouse `rz_epa_raw` stored, **unwired**. |

#### KE Havoc / Disruption

| Axis          | Live                                                                                                          | Research                                                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Class**     | **MISSING** (UI copy)                                                                                         | **PARTIAL** flags / **NEEDS_VALIDATION**                                                                                                                                                  |
| **Live UI**   | `sport-config.ts` labels Tempo / Havoc / Explosiveness / Success; team-research sections `status: "pending"`. | 2026 raw: `havoc`, `TFL`, `sack`, `int`, `pass_breakup`, `forced_fumble` present (#558). Charted official TFL / PBU **not** certified. `owned_metrics` explicitly out of scope for havoc. |
| **Warehouse** | —                                                                                                             | `stuff_rate` measured on team-game; **unwired**.                                                                                                                                          |

#### EPA / PPA

| Axis    | Live                   | Research                                                                                      |
| ------- | ---------------------- | --------------------------------------------------------------------------------------------- |
| **EPA** | **MISSING** (not used) | **REAL_UNVALIDATED** raw + **REAL_UNVALIDATED** #560 adj (EPA-prediction sealed, not ratings) |
| **PPA** | **MISSING**            | **MISSING** (optional). CFBD parked. Do not buy a feed.                                       |

`EPA_success = EPA>0` — 1.000 agreement on 2021–24 scrimmage (#555). Standard 50/70/100 SR is a **separate** column. Do not conflate them.

#### Opponent adjustment

| Axis             | Live                               | Research                                                                                                                                              |
| ---------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Class**        | **PROXY** (vendor SP+ methodology) | Warehouse 4-iter: **REAL_UNVALIDATED**. #560: **REAL_UNVALIDATED** (ADVANCE on EPA MAE)                                                               |
| **#560 formula** | —                                  | Joint ridge; FBS off/def centered 0; FCS `λ_fcs=4λ`; OT `period≥5` dropped; garbage weight min 0.10; `n_games<2` flagged; week-1 = decayed prior only |
| **Not**          | —                                  | A point spread. Season-final `h` ~0.05–0.07 EPA/play. 2026 W1–2 `h≈0.244` is a thin-window intercept. **Forbidden:** `0.244 × n_plays` as HFA (#562). |

#### Strength of schedule

| Axis            | Live                                                                          | Research                                                              |
| --------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **Class**       | **PARTIAL**                                                                   | **PARTIAL** / implicit                                                |
| **What exists** | Implicit in vendor SP+ and in season-sim opponent indices. No owned SOS book. | Opponent identity is inside the #560 two-way; no published SOS table. |

#### Power ratings / team strength

| Axis               | Live                                                                                                                  | Research                                               |
| ------------------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Class**          | **REAL_UNVALIDATED**                                                                                                  | #560 efficiencies are **not** power ratings            |
| **Live formula**   | Compose 0–100 mix → index. `power_index = 0.5*(offense_index + defense_index)`. Frozen `cfb_power_sot_2026.json`.     | —                                                      |
| **Scoring (live)** | `base = 25.9 * (off/def)^1.40 * unit_boosts * pace` + variable HFA (~1.7 baseline) + coaching point drag. Clamp 7–55. | #562 research conversion **REVISE** — separate, unused |
| **UI**             | `/pro/cfb/model`, project-game; `/pro/power-ratings/cfb` empty unless JSON added; teams census parked                 | None                                                   |

#### Returning production / units / coaching — **not football efficiency**

These are **identity / prior layers**. They must not be inventoried as KE Off/Def/ST/Pace/Explosiveness/Finishing/Havoc.

| Signal               | Formula / default                                                                                                                               | Class                                                                       |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Returning production | `100 * (0.65*snap_share + 0.35*start_share)`. Default `returning_production=50`, snap/start 0.50. Packaged ESPN 2026 roster is **approximate**. | **PROXY** of roster continuity, **CONSTANT_OR_50_FILL** when shares missing |
| Roster strength      | `0.32*returning + 0.26*portal_net + 0.26*recruiting + 0.16*experience`                                                                          | PROXY composite                                                             |
| Unit grade           | `0.50*talent + 0.30*experience + 0.20*portal`. Soft-fills from roster when packaged units are flat 50s (`fidelity=placeholder`)                 | **CONSTANT_OR_50_FILL** / PROXY                                             |
| QB situation         | Class multipliers (incumbent 1.06 … true_freshman 0.79) + cast scale 0.11. Defaults 50.                                                         | PROXY                                                                       |
| Coaching             | Curated 2026 staff flags. `NEW_HC_OFF_INDEX=0.965`, week-decayed point penalties (HC off 1.35, DC def 1.20, …). Labeled approximate             | PROXY / curated constants                                                   |
| Hist-cal universe    | `historical_calibration.build_historical_proxy_state`: roster/QB/units **all 50**; `expl = 50 + 0.15*(off−def)`; `success_off = off_eff`        | **CONSTANT_OR_50_FILL** + PROXY                                             |

`docs/CFB_CH2_TALENT_VOLUME_*` and CH2 QB briefs document these as identity, not EPA.

### 4.5 Explicit CFB 50-fill / constant inventory (live)

| Location                    | When                                 | Value                               | Class                        |
| --------------------------- | ------------------------------------ | ----------------------------------- | ---------------------------- |
| Efficiency snapshot         | 6 of 147 teams `league_average_fill` | all eff fields **50.0**             | CONSTANT_OR_50_FILL          |
| `build_efficiency_profile`  | Non-FBS / missing code               | 50.0 all eff                        | CONSTANT_OR_50_FILL          |
| Official FBS missing SP+    | Packager / loader                    | **Hard-fail**                       | Guard (good)                 |
| `compose_team_projection`   | `efficiency is None`                 | `off_eff=def_eff=50`                | CONSTANT_OR_50_FILL          |
| `types.py` defaults         | Missing grades                       | Most unit/QB/roster fields **50.0** | CONSTANT_OR_50_FILL          |
| `position_groups`           | All units ≈50                        | `fidelity=placeholder`              | CONSTANT_OR_50_FILL          |
| Warehouse / #560 cold start | No games yet                         | adj EPA **0** (league-centered)     | CONSTANT (EPA scale, honest) |
| `power_sot_v0.15_fill`      | Slate code lacks compose             | Placeholder indices from pack       | PLACEHOLDER                  |
| `thin_sample_labeled`       | Referenced, no producer              | —                                   | DEAD_CODE                    |

### 4.6 2026 W−1 research facts (do not regress)

| Fact                             | Value                                                              |
| -------------------------------- | ------------------------------------------------------------------ |
| #559 snapshot eligible           | 85 completed ∩ PBP ∩ week &lt; 3                                   |
| #560 closed eligible             | **84** (`401868140` excluded: PBP Q2 28–0 vs official 49–7)        |
| PBP SHA                          | `da0ec956…`                                                        |
| Schedule SHA                     | `bbc26106…`                                                        |
| `opponent_adjusted` on #559 rows | **false**                                                          |
| #560 2026 apply                  | 84 games / 168 obs / 134 FBS; 42 prior-only; `μ=−0.106`, `h=0.244` |
| HD Aug 13 lake                   | **not written**                                                    |

A score alone is not eligibility. DELAYED + incomplete PBP = exclude.

---

## 5. Shared / cross-sport football (what is actually shared)

| Piece                         | Shared?              | Notes                                                                                                 |
| ----------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------- |
| Season-engine folder pattern  | Plumbing only        | `nfl_season_engine/` vs `cfb_season_engine/` — not one library                                        |
| O/D index ~1.0                | Convention           | NFL 0.82–1.24 clamps; CFB 0.52–1.68. Different identity of “1.0”                                      |
| Carry shrink toward mean      | Idea only            | NFL `games/8`; CFB `EFF_CARRY_SHRINK=0.85` on 0–100                                                   |
| Opponent-adjust iterator      | Idea only            | NFL KAV 12-iter; CFB warehouse 4-iter; CFB #560 joint ridge. **Three estimators, zero shared module** |
| KEI `model_*` vs `handicap_*` | Product layer        | Downstream of ratings. Shared **contract**, not shared math                                           |
| `/pro/power-ratings/[sport]`  | UI shell             | NFL desk JSON only. CFB empty unless SoT JSON added                                                   |
| Garbage-time                  | CFB warehouse / #560 | NFL uses nflverse `success` / score differential in ingest; not the same weights                      |
| Explosive definition          | **Not shared**       | NFL 20-yd pass / KAV 12-yd / CFB EPA≥1 or 15 yd                                                       |
| Success definition            | **Not shared**       | NFL nflverse `success`; CFB `EPA>0` plus optional 50/70/100                                           |
| PPA                           | Neither              | Optional; absent                                                                                      |
| PFF                           | Neither              | **Do not purchase**                                                                                   |
| Feature mart schema           | No                   | `nfl_dp_*` vs CFB warehouse / research folders                                                        |

**Implication:** a canonical KE Football feature layer can be **conceptual** across sports. It cannot be a copy-paste of NFL v1.1 into CFB compose, or of #560 into NFL Layer-1.

---

## 6. Dependency graph (football only)

```text
NFL PBP EPA/success/explosive-pass/RZ/pressure/ST
        │
        ├─ efficiency_backbone ──► TeamStrengthState ──┬─ expected_team_points
        │                                              ├─ power_ratings_desk ─ (dark) /pro/power-ratings/nfl
        │                                              ├─ true_pr_product ─ (dark) /pro/nfl/model
        │                                              └─ (dark) Edge Board
        ├─ KAV ──► matchup / handicapping / sim        (NOT Layer-1 PR)
        └─ player production spine                     (NOT KE ratings)

SP+ 2025 ──► 0–100 pack + SYNTHETIC success/expl ──► compose ──► (dark) KEI
Roster / QB / units / coaching ─────────────────────┘
PBP research ──► #559 raw ──► #560 adj EPA ──► #562 scoring (REVISE)
                 └── warehouse 4-iter ──► research_prior only
```

### What looks like ratings and is not

- CFB live explosiveness / success / pace
- CFB `/pro/cfb/tempo` and havoc card
- Team-research Tempo/Havoc/Explosiveness/Success (`pending`)
- Returning production, portal, recruiting, unit grades, curated coaching
- #560 EPA as a spread
- #562 points as a production scoring model
- NFL structural-pace UI pack
- NFL KAV as a second Model PR
- Player production / fantasy spine

---

## 7. Validation evidence index (existing — no new fits)

| Area                  | Evidence                                                                 | What it validates                          |
| --------------------- | ------------------------------------------------------------------------ | ------------------------------------------ |
| NFL backbone          | `test_nfl_efficiency_backbone.py`, ops v1 / v1.1                         | Hierarchy smell; ST/splits labels          |
| NFL Past SOS          | `test_nfl_adjusted_sos_past.py`                                          | Prior-only schedule adjust                 |
| NFL Power desk        | `test_nfl_power_ratings_desk.py`, Tuesday runbook                        | Method B, zero-center, α                   |
| CFB compose           | `test_cfb_season_engine.py`, CH2 scorecards                              | Eff moves projections; FBS hard-fail       |
| CFB warehouse leakage | `test_cfb_warehouse_leakage.py`                                          | PIT week `< W`                             |
| CFB totals hot        | `docs/CFB_TOTALS_HOT_AUDIT.md`                                           | Pace/expl **not** the Over                 |
| CFB raw metrics       | `test_cfb_owned_pbp_metrics.py`, `test_cfb_2026_w1_team_game_metrics.py` | Definitions + 2026 eligibility (research)  |
| CFB #560              | `test_cfb_research_opp_adj.py`, audit note                               | Next-game EPA MAE; 2025 not in λ selection |
| CFB #562              | `docs/cfb/CFB_RESEARCH_EFF_SCORING_2026-09-15.md` (on #562 branch)       | **REVISE** — totals miss                   |
| Reopen tracker        | `docs/ops/FOOTBALL_NUMBERS_REOPENING_TRACKER.md`                         | Boards dark; EPA ADVANCE ≠ reopen          |

---

## 8. STOP

This document is an **inventory**. It does not design a migration, rematerialize order, or permission to:

- unwire SP+
- promote #560 onto KEI
- retune #562 `a`/`b`/pace
- loosen the totals gate
- reopen boards
- buy PFF or shop vendors
- treat returning production / units / coaching as measured efficiency
- start NFL remediation from this note

**For Ryan / CoS review.** Architecture and data requirements are in the companion file. No implementation authorized here.

---

## Appendix A — Key file index

| Path                                                                           | Role                                   |
| ------------------------------------------------------------------------------ | -------------------------------------- |
| `services/model-service/src/services/nfl_season_engine/efficiency_backbone.py` | NFL owned ratings-like spine           |
| `services/model-service/src/services/nfl_season_engine/adjusted_sos.py`        | NFL past SOS                           |
| `services/model-service/src/services/nfl_season_engine/power_ratings_desk.py`  | Method B Model PR                      |
| `services/model-service/src/services/nfl_season_engine/team_strength.py`       | `expected_team_points`                 |
| `services/model-service/data_platform_nfl/kav.py`                              | KAV (not Layer-1)                      |
| `scripts/nfl/build_packaged_efficiency_backbone.py`                            | NFL packaged artifact                  |
| `services/model-service/src/services/cfb_season_engine/efficiency.py`          | SP+ profile loader                     |
| `scripts/cfb/package_efficiency_2025_carry.py`                                 | SP+ z-map + **synthetic** success/expl |
| `services/model-service/src/services/cfb_season_engine/team_projection.py`     | Compose + pace proxy + ST nudge        |
| `services/model-service/src/services/cfb_season_engine/roster_construction.py` | Returning production (not EPA)         |
| `services/model-service/src/services/cfb_season_engine/coaching_continuity.py` | Curated staff constants                |
| `services/model-service/src/services/cfb_warehouse/efficiency_adj.py`          | Warehouse 4-iter EPA (research)        |
| `services/model-service/src/services/cfb_warehouse/owned_metrics.py`           | #555 raw definitions                   |
| `services/model-service/src/services/cfb_warehouse/team_game_w1_2026.py`       | #559 W−1 raw table                     |
| `services/model-service/src/services/cfb_warehouse/research_opp_adj.py`        | #560 joint-ridge EPA                   |
| `apps/web/app/(pro)/pro/[sport]/tempo/page.tsx`                                | CFB tempo **placeholder**              |

## Appendix B — Prior artifacts this inventory relied on

- #556 `docs/ratings/KE_RATINGS_ENGINE_EXISTING_INVENTORY_2026-09-15.md` (open PR; not on `deploy-vercel` yet)
- #558 amendment + NFL/CFB gap matrix (open PR)
- `docs/cfb/CFB_OWNED_DATA_INVENTORY_GAP_2026-09-15.md`
- `docs/cfb/CFB_2026_W1_RAW_TEAM_GAME_METRICS_2026-09-15.md`
- `docs/cfb/CFB_RESEARCH_OPP_ADJ_EPA_2026-09-15.md` + audit
- #562 scoring note (open PR; totals **REVISE**)
- `data/ops/nfl-efficiency-backbone-v1.1-20260808.md`
- `data/ops/cfb-efficiency-backbone-20260804.md`
- `docs/ops/FOOTBALL_NUMBERS_REOPENING_TRACKER.md`

---

_End of football inventory. 2026-09-15. No implementation._
