# KE Football Ratings Engine v1 — DESIGN SPEC

**Date:** 2026-09-15  
**Status:** `MEASUREMENT_PHASE1` · `production_promote=false`  
**Authority:** Ryan review of [#569](https://github.com/kosedge/kosedge/pull/569) → **GO Phase 1 measurement only.**  
**Taxonomy amend:** [`KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md`](./KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md) **supersedes §2 layer list** (RAW → DERIVED → ADJUSTED → MODELED).  
**Companions:** [`KE_FOOTBALL_V1_METRIC_MATRIX.md`](./KE_FOOTBALL_V1_METRIC_MATRIX.md) · [`KE_FOOTBALL_V1_METRIC_MATRIX.json`](./KE_FOOTBALL_V1_METRIC_MATRIX.json)  
**Built on:** [`KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md`](./KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md) · [`KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md`](./KE_FOOTBALL_GAP_MATRIX_AND_ARCHITECTURE_2026-09-15.md)

This document remains the metric-definition SoT. Phase 1 **implements measurement + PIT ADJUSTED EPA + disruption inventory + validation**. It does **not** implement Team Strength, scoring, matchup, market, UI, or board reopen. It does not rematerialize production tables.

---

## 0. Hard stops

| Forbidden                                                        | Why                                                                                                                          |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Implementation / fitting / production writes                     | This assignment is design only.                                                                                              |
| UI changes / board reopen                                        | Boards stay dark (#561). Flags stay false.                                                                                   |
| New scoring equation                                             | #562 **REVISE** (margin helped, totals missed). Do not loosen. Do not retune `a`/`b`/pace because totals missed.             |
| Using #562 as coefficient justification                          | Scoring failure is a **scoring-layer** fact. It is not evidence that explosiveness, pace, or efficiency weights should move. |
| Promoting #559 / #560                                            | Reconcile into this design. `production_promote` stays false. Not KEI. Not a spread.                                         |
| PFF / new vendors / CFBD purchase                                | Owned data only. PPA is optional and absent. Missing PPA ≠ buy a feed.                                                       |
| Synthetic proxy labeled as the real metric                       | Live CFB SP+ z → fake success / explosiveness / skill−F7 pace stay **PROXY**, never KE.                                      |
| Silent 50-fill / identity constant                               | Official teams missing required information → `DATA_INSUFFICIENT` or an explicitly documented **partial** rating.            |
| ATS / close / betting ROI as construction loss                   | First validation is football predictive validity. Market comparison is the **last** stage, after ratings exist.              |
| Copying NFL numbers onto CFB to finish the schema                | Shared **names**. Sport-specific priors, stabilization, roster handling, opponent adjustment.                                |
| Relabeling returning production / units / coaching as efficiency | Identity layer. Visible. Not a substitute for measurement.                                                                   |
| Starting NFL remat / #564 / #567 from this spec                  | Separate track.                                                                                                              |

**NFL is the reference implementation.** The owned nflverse play-level spine is materially stronger than CFB live compose. CFB may share metric definitions and infrastructure patterns. CFB must not inherit a league-average, a 50, or an NFL knob just so a cell is non-empty.

---

## 1. Architecture

```text
data truth
  → football measurement
    → opponent adjustment
      → team strength
        → matchup interaction
          → scoring projection
            → market comparison
```

| Stage                | v1 status         | What v1 specifies                                                                                                |
| -------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| Data truth           | **In spec**       | Play/game SoT, SHA, eligibility, identity, fail-closed incomplete PBP                                            |
| Football measurement | **In spec**       | Off / Def / ST / Pace / Explosiveness / Finishing / Havoc                                                        |
| Opponent adjustment  | **In spec**       | KE Opponent-Adjusted EPA (O/D EPA/play only)                                                                     |
| Team strength        | **In spec**       | KE Overall from adj O/D in **native EPA units**                                                                  |
| Matchup interaction  | **Boundary only** | Consumes the book. Not designed here. Not a rating.                                                              |
| Scoring projection   | **Boundary only** | Downstream. Frozen-failed CFB #562 is not the house model. NFL `expected_team_points` remat is a separate track. |
| Market comparison    | **Boundary only** | After ratings exist. Not a construction objective. Boards remain dark.                                           |

A working (or parked) board is not a ratings engine. A sealed EPA MAE is not a spread. A failed totals conversion is not permission to write a new scoring equation.

---

## 2. Four layers

Every KE number declares exactly one layer. Mixing them without a label is a spec violation.

**Amend (2026-09-15, #569 review):** RAW → DERIVED → **ADJUSTED** → MODELED. Opponent adjustment is **ADJUSTED** unless a genuinely fitted predictive model is involved. **MODELED** is reserved for estimated/fitted outputs (#560 joint-ridge is MODELED and is **not** Phase 1). See [`KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md`](./KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md).

| Layer        | Meaning                                                     | Allowed                                                                                                     | Forbidden                                                                   |
| ------------ | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **RAW**      | Directly observed football events / statistics              | Play flags, yards, EPA column as published by the owned PBP source, down, distance, score, clock, play type | A z-score, a 0–100, a ridge estimate, a 50                                  |
| **DERIVED**  | Deterministic KE calculation from RAW                       | Means, rates, plays/game, opportunity / PPO, seconds/play when clock is certified                           | Opponent effects; silent league-average substitution; SP+ z heuristics      |
| **ADJUSTED** | Deterministic PIT opponent adjustment of a DERIVED quantity | Leave-one-game-out SOS; `week < W` only                                                                     | Fitted `off_i`/`def_j`; ridge; silent league fill when opponent has no book |
| **MODELED**  | Fitted / estimated values                                   | Two-way EPA (`off_i`, `def_j`), decayed priors, ridge — **not Phase 1**                                     | A synthetic “success” invented from SP+; an identity constant named as EPA  |

Rules:

1. No synthetic proxy may be labeled as the real metric.
2. No 50-fill or identity constant may silently enter a KE rating.
3. Missing required information → `DATA_INSUFFICIENT` **or** an explicitly documented partial rating (`partial=true`, named missing fields, native fields that remain valid).
4. Retain **native football values** (EPA/play, success rate, seconds/play, plays/game, opportunity rate). League-average-centered 0–100 / 1.00 index is a **later display layer**, not the identity of the rating.
5. Do not optimize against ATS, closing lines, or betting ROI during construction.
6. First validation = football / out-of-sample predictive validity (see §4).

Live NFL `offense_index` / `defense_index` (clamped ~0.82–1.24, EPA + pressure + soft additives) is a **product mapping** onto `TeamStrengthState`. It is **not** the v1 identity of KE Offensive or Defensive Efficiency.

Live CFB 0–100 SP+ carry, synthetic success / explosiveness, and skill−F7 pace are **not** KE ratings.

---

## 3. Data truth (both sports)

### 3.1 One play-level SoT per sport

|                    | NFL (reference)                                                    | CFB                                                                                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source             | nflverse / nflreadpy PBP already ingested                          | SportsDataverse `espn_cfb_pbp` already owned                                                                                                                                                        |
| Canonical store    | `nfl_dp_play_by_play` (+ raw payloads in `nfl_dp_raw_objects`)     | HD lake `/Volumes/KosEdgeData/raw/cfb/pbp/` (2014–2025, do not overwrite) + versioned `pbp_current/as_of_YYYYMMDD/` for 2026+                                                                       |
| Worker readability | Postgres marts exist                                               | Railway has **no** CFB parquet volume today. Research files on a laptop HD are not a production feature store. Platform copy is required before any live CFB KE; that is **not** a vendor purchase. |
| Identity           | Product aliases (`LA`→`LAR`). Official clubs hard-fail if missing. | Official FBS hard-fail (keep). FCS flagged, not deleted. No 50-fill for official FBS.                                                                                                               |
| SHA / as_of        | Ingest run + week cap                                              | Input SHA on every research table (#559/#560 pattern)                                                                                                                                               |

PPA is **optional and absent**. KE v1 is EPA-centered. Do not buy CFBD or PFF to complete PPA.

### 3.2 Completed-game eligibility (fail-closed)

A score alone is not eligibility. Learned on CFB `401868140` (#560): DELAYED + partial Q2 PBP (28–0) vs official 49–7.

**Include a game only if all of:**

1. Schedule status is a true final (`STATUS_FINAL` / NFL completed-game gate).
2. Official final score is present and not a live/period/delayed leftover.
3. PBP reaches the official final (period complete; scoring markers match; not a Q2 cut).
4. Feature week `W` uses only games with `week < W` (strict PIT).

**Exclude:** live, HALFTIME, END_PERIOD, DELAYED-without-complete-PBP, completed-missing-PBP, unmatched PBP, overtime plays from EPA means (`period/qtr ≥ 5` for CFB adj; NFL OT stays in RAW but is **excluded** from MODELED EPA v1 unless a later sealed note includes it).

NFL already gates on schedule scores. Keep that honesty. Do not loosen CFB to “score present and not live.”

### 3.3 Shared scrimmage filter

| Sport | Scrimmage                                                               | Special teams                                                           |
| ----- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| NFL   | `play_type ∈ {pass, run}` with finite `epa` (and `posteam` / `defteam`) | `play_type ∈ {field_goal, extra_point, punt, kickoff}` — ST rating only |
| CFB   | truthy `scrimmage_play`, else truthy `pass` or `rush`; finite `EPA`     | ST rating only; not in O/D denominators                                 |

Kneel / spike / untagged / missing EPA → drop from that metric’s denominator. Do not impute EPA.

### 3.4 Garbage / blowout

| Sport | v1 rule                                                                                                                                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFL   | RAW/DERIVED unadjusted rates are **unweighted**. MODELED EPA may apply a documented garbage weight later; v1 default is **unweighted** until a sealed NFL garbage study exists. Do not copy CFB weights onto NFL. |
| CFB   | RAW/DERIVED unadjusted = unweighted (same as #555/#559). MODELED opponent-adjusted EPA uses warehouse `garbage_weight` (min 0.10, not a hard drop) — research candidate only, frozen with #560.                   |

Garbage belongs in measurement notes, not hidden inside a z-score.

---

## 4. Validation doctrine (all ratings)

Construction loss and first gate are **football**, not market.

**Primary tests (required before a rating may be called KE v1):**

1. **Future unit performance** — next-game (or next-week) same-unit metric. Offense ratings predict future offensive EPA/play and success; defense ratings predict future EPA allowed and success allowed.
2. **Scoring outcomes where appropriate** — margin and points are allowed as **secondary** checks for Overall / Team Strength only. They are not the construction loss for Off/Def/ST/Pace/Explosiveness/Finishing/Havoc. Totals and spreads are **separately** gated downstream.
3. **Stability** — week-to-week rank/value movement vs sample size; no cliff after 1–2 games if a prior exists.
4. **Calibration** — predicted vs realized EPA (or rate) by decile; bias reported.
5. **Incremental value** — beat simpler baselines: (a) unadjusted season-to-date, (b) prior-season blend / decayed prior, (c) league mean. Report MAE / RMSE / bias / n / early-season (W1–4) split.

**Forbidden as construction or as a reason to change knobs:**

- ATS, closing-line error, betting ROI, KEI lift
- “Totals missed, therefore raise explosiveness weight” (#562)
- Hierarchy smell **alone** (SEA ≫ ARI is a sanity check, not a seal)

**Holdout rule:** selection years ≠ holdout year. #560 already: λ/n0/decay on 2023–2024 only; 2025 sealed. NFL v1 MODELED estimators must name selection vs holdout the same way.

**Display-scale tests are last.** Native-unit tests come first.

---

## 5. Status and failure vocabulary

| Code                | Meaning                                                                      |
| ------------------- | ---------------------------------------------------------------------------- |
| `OK`                | Required inputs present; rating computed                                     |
| `THIN`              | Computed but below sample floor; `prior_weight` and `n` must be visible      |
| `PRIOR_ONLY`        | No current-season eligible games; decayed prior only; labeled                |
| `PARTIAL`           | Documented subset of the rating (named fields present, named fields missing) |
| `DATA_INSUFFICIENT` | Required information missing; **no number**                                  |
| `EXCLUDED_GAME`     | Game failed eligibility; omitted from all aggregates                         |

`DATA_INSUFFICIENT` is a first-class output. It is not a 50, not `1.0`, not `0.0` pretending to be league average — except **MODELED EPA priors**, which are **league-centered 0 on the EPA scale** and must be labeled `PRIOR_ONLY` (honest EPA intercept, not a 50-fill).

Official FBS / official NFL club missing a required SoT → `DATA_INSUFFICIENT` or hard-fail at pack time. Never `league_average_fill=50`.

---

## 6. Identity layer (not a KE rating)

These may **prior** a rating early in the season if a later assignment says so. They must never **replace** measurement or fill a missing KE cell.

| Signal                                               | Sport | Class                                                                                                                    |
| ---------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------ |
| Returning snap/start, portal, recruiting, experience | CFB   | PROXY / 50-fill today — **not KE**                                                                                       |
| QB class multipliers                                 | CFB   | PROXY — **not KE**                                                                                                       |
| Curated HC / OC / DC flags                           | CFB   | PROXY — **not KE**                                                                                                       |
| Injury overlay, QB premium hook, continuity flags    | NFL   | PROXY / PARTIAL — **not KE**                                                                                             |
| SP+ 2025 snapshot                                    | CFB   | Vendor prior. Labeled vendor. Competing prior only if a later assignment says so. **Never** fake success / explosiveness |

`ke.identity_*` stays visible and separate.

---

## 7. Canonical rating specs

Shared field order for every rating:

raw inputs → exclusions → mathematical definition → opponent adjustment → stabilization → prior/decay → normalization/display → PIT → cadence → validation → failure.

Native unit is the rating. Display index is later.

---

### 7.1 KE Offensive Efficiency

|                                       |                                                                                                                                  |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **ID**                                | `ke.off_eff`                                                                                                                     |
| **Question**                          | How many expected points does this offense create per eligible scrimmage play?                                                   |
| **Layer**                             | **DERIVED** (unadjusted). ADJUSTED counterpart is Phase 1 `ke.opp_adj_epa`. MODELED counterpart is the #560 ridge (not Phase 1). |
| **Native unit**                       | EPA/play (higher better)                                                                                                         |
| **Required companion (not mixed in)** | Success rate — see §7.1.1                                                                                                        |

This rating **is** offensive EPA/play. It is **not** the NFL backbone composite `1.0 + 0.75*off_epa + pressure + soft additives`. It is **not** CFB `50 + 18*z(SP+ offense)`.

#### Raw inputs

| NFL                                                                                                                                                            | CFB                                                                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `nfl_dp_play_by_play.epa`, `success`, `play_type`, `posteam`, `down`, `ydstogo`, `yards_gained`, `passing_yards`, `rushing_yards`, `season`, `week`, `game_id` | SDV `EPA`, `EPA_success`, `scrimmage_play` / `pass` / `rush`, `pos_team`, `down`, `distance`, `statYardage`, `season`, `week`, `game_id` |

Pass / run / early-down EPA are **diagnostic splits**, not a second offensive rating.

#### Exclusions / filtering

Shared §3.2–3.3. Offense row = team as `posteam` / `pos_team`. Drop non-finite EPA. Drop ST plays. CFB MODELED path additionally drops OT (`period ≥ 5`); DERIVED unadjusted v1 **includes** OT scrimmage unless the game itself is excluded.

#### Mathematical definition

```text
ke.off_eff(team, window) = Σ EPA_i / n
  i ∈ eligible offensive scrimmage plays in window
  n = count of those plays
```

Window = one team-game (grain 0) or season-to-date with `week < W` (grain 1).

**§7.1.1 Success companions (DERIVED, not collapsed into EPA):**

| ID                    | Definition                    | NFL                                                                                    | CFB                                                                                             |
| --------------------- | ----------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `ke.success_native`   | Sport-native success column   | nflverse `success`                                                                     | `EPA_success` ≡ `EPA > 0` (#555: 1.000 agreement on 2021–24 scrimmage)                          |
| `ke.success_standard` | Football Study Hall 50/70/100 | Same family as nflverse success; **audit agreement** before treating them as identical | #555 `standard_success_rate` (1st ≥50% of `distance`, 2nd ≥70%, 3rd/4th ≥100% of `statYardage`) |

Do not silently swap `EPA_success` and 50/70/100. They agreed **0.940** on 2021–24 CFB scrimmage. Both columns stay. Neither is “50.”

#### Opponent adjustment

**None on this rating.** Unadjusted. Opponent-adjusted EPA is §7.8.

#### Stabilization / sample

|                                | NFL                                                                                        | CFB                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Team-game publish              | `n_plays ≥ 1` else `DATA_INSUFFICIENT`                                                     | same                                                                       |
| Season-to-date publish         | `n_plays ≥ 25` or `n_games ≥ 1` with `THIN` if `n_plays < 80`                              | `n_plays ≥ 25` or `n_games ≥ 1`; `THIN` if `n_games < 2` or `n_plays < 80` |
| Split publish (pass/run/early) | NFL floors already in backbone (`200` / `150` / `250`) — keep as **labels**, do not invent | Same idea; sport-specific floors; missing split → omit split, not fill     |

No silent league-mean EPA when `n=0`.

#### Prior / decay

DERIVED unadjusted has **no prior mixed into the number**. A prior is a MODELED / bookkeeping field (`prior_off_epa`) stored beside it. Early season: publish raw + `PRIOR_ONLY` adj book, not a blend labeled as raw.

#### Normalization / display

Native EPA/play. Later display may be league-centered (`raw − μ_league`) or a 0–100 index. Display must cite `ke.off_eff` and `as_of`. Clamped 1.00-index is **not** this rating.

#### Point-in-time

Week `W` uses games with `week < W` only. Packaged prior-season files are priors, not current `ke.off_eff`.

#### Update cadence

| NFL | After each completed eligible game; weekly rematerialize of situational / rolling marts. |
| CFB | After each eligible-as_of cut (versioned `pbp_current`). Research cadence until a worker volume exists. |

#### Validation test

Predict **next-game offensive EPA/play** and `ke.success_native`. Baselines: league mean, trailing unadjusted mean. Report MAE/RMSE/bias. Do not use ATS.

#### Failure behavior

| Condition                 | Output                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------ |
| No eligible plays         | `DATA_INSUFFICIENT`                                                                        |
| Incomplete PBP game       | game `EXCLUDED_GAME`; do not average a Q2 cut                                              |
| Official team missing SoT | hard-fail / `DATA_INSUFFICIENT` — no 50                                                    |
| EPA column null on a play | drop play; if null rate on used scrimmage > 1%, flag `PARTIAL` and do not pretend complete |

#### Buildability today

| NFL | **YES** — nflverse EPA is live on the spine. |
| CFB | **YES_RESEARCH** — #555/#559 definitions + 2026 closed 84-game table. Not live compose. Worker volume still missing for production. |

#### Forbidden substitutions

SP+ offense z, returning production, unit grades, backbone `offense_index`, `placeholder_league_avg=1.0`.

---

### 7.2 KE Defensive Efficiency

|                 |                                                                               |
| --------------- | ----------------------------------------------------------------------------- |
| **ID**          | `ke.def_eff`                                                                  |
| **Question**    | How many expected points does this defense allow per eligible scrimmage play? |
| **Layer**       | **DERIVED** (unadjusted)                                                      |
| **Native unit** | EPA/play **allowed** (lower better)                                           |

Mirror of §7.1 with `defteam` / `def_pos_team`. Success allowed uses the same two companions.

```text
ke.def_eff(team, window) = Σ EPA_i / n
  i ∈ eligible scrimmage plays faced
```

Do **not** invert the native unit to “higher better” inside the rating. Inversion is a display choice.

Opponent adjustment: none here. Phase 1 `ke.opp_adj_epa` defense is the **ADJUSTED** allowed EPA. The #560 ridge remains MODELED research.

Stabilization, prior, PIT, cadence, validation, failure: same structure as offense, predicting **future EPA allowed**.

NFL live `defense_index = 1.0 + (−def_epa)*0.90 + …` is not this rating.

CFB live `50 + 18*z(inverted SP+ defense)` is not this rating.

#### Buildability today

| NFL | **YES** |
| CFB | **YES_RESEARCH** (same as offense) |

NFL remaining honesty (from ops v1.1, not a fake fill): defense-allowed RZ and rolling pass/run/early-down EPA are **partial on the live rolling path**. v1 DERIVED defense EPA/play does not require those splits. Missing splits → omit splits (`PARTIAL` on the split package), not a 0.55 RZ fill inside `ke.def_eff`.

---

### 7.3 KE Special Teams Efficiency

|                 |                                                                                    |
| --------------- | ---------------------------------------------------------------------------------- |
| **ID**          | `ke.st`                                                                            |
| **Question**    | How many expected points does this special-teams unit create per eligible ST play? |
| **Layer**       | **DERIVED** when ST EPA exists; otherwise **not published**                        |
| **Native unit** | ST EPA/play (kicking-team frame; higher better)                                    |

#### Raw inputs

| NFL                                                                                                                                              | CFB                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `play_type ∈ {field_goal, extra_point, punt, kickoff}`, `epa`, `posteam`, `defteam` — already used by `build_st_kav_weekly.py` (cited 2013–2025) | SDV `type.text` plus ~83 ST-ish columns on 2026 raw; **completeness not certified**. No ST EPA product. Kickoff EPA frame not defined. |

NFL kickoff frame (owned, keep): FG/XP/punt EPA as-is on `posteam`; kickoff EPA **negated** onto `defteam` (kicking side in nflverse).

#### Exclusions

Non-ST plays. Null EPA. Games failing §3.2. Do not use offensive EPA as a stand-in.

#### Mathematical definition

```text
ke.st(team, window) = Σ st_epa_i / n_st
```

KAV-like `(st_epa − μ) / 0.20` is a **display / matchup-pack** transform already in the NFL builder. It is **not** the KE rating.

#### Opponent adjustment

**None in v1.** No sealed two-way for ST. #560 already left ST as supporting raw. Do not pretend SOS-adjusted ST.

#### Stabilization / sample

| NFL | `n_st ≥ 8` for a team-game; season-to-date `THIN` below 40 ST plays (backbone `_THIN_ST_PLAYS`). Below floor → `THIN` or omit, **not** `st_index=1.0`. |
| CFB | No certified denominator. **Do not publish.** |

#### Prior / decay

No silent `1.0` / `50` prior. If a prior ST EPA exists from last season and current `n_st=0`, output `PRIOR_ONLY` with that EPA **or** `DATA_INSUFFICIENT`. v1 default: `DATA_INSUFFICIENT` until last-season ST EPA is certified.

NFL live `missing ST → st_index=1.0 neutral_hook` is **CONSTANT_OR_50_FILL**. v1 forbids that hook inside `ke.st`.

#### Normalization / display

Native ST EPA/play. Index 0.85–1.15 is display.

#### Point-in-time / cadence

NFL: weekly ST KAV table is as-of end of W; pregame joins use W−1 (already documented). Keep.  
CFB: no cadence until completeness audit.

#### Validation test

NFL: predict next-game ST EPA/play vs league mean and trailing mean. Secondary: FG make residual and net punt/return EPA if those splits exist — splits are diagnostic.  
CFB: **no validation until completeness**. Flags-exist is not a test.

#### Failure behavior

| NFL missing ST plays | `DATA_INSUFFICIENT` (not 1.0) |
| CFB uncertified columns | `DATA_INSUFFICIENT` — omit the rating |
| Charted ST grades (PFF) | Forbidden |

#### Buildability today

| NFL | **YES** as DERIVED ST EPA/play from owned PBP. **NEEDS_VALIDATION** as a sealed KE module (inventory: REAL_UNVALIDATED). Play-count approximation (~8/game) on live labels must be replaced by exact PBP `n_st`. |
| CFB | **NO** — types/flags exist; completeness not certified; no ST EPA. Omit > impute. |

#### Forbidden substitutions

Unit-grade `special_teams=50`, compose `0.015 * ((st−50))` nudge, unused packaged `sp_special_teams`, PFF.

---

### 7.4 KE Pace

|                 |                                                          |
| --------------- | -------------------------------------------------------- |
| **ID**          | `ke.pace`                                                |
| **Question**    | How many scrimmage plays does this offense run per game? |
| **Layer**       | **DERIVED**                                              |
| **Native unit** | Plays / offense-game                                     |

Seconds/play is a **companion** (`ke.pace_seconds`), not a replacement.

#### Raw inputs

| NFL                                                                                                                                                                                                 | CFB                                                                                                                                          |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Eligible offensive scrimmage count per `game_id`; `game_seconds_remaining` (column exists via `043_nfl_second_order_edge.sql` — publish seconds/play only if null rate on used plays is acceptable) | #555: scrimmage as `pos_team` per team-game; `pos_score_diff` for competitive pace; `start.TimeSecsRem` in core-31 for optional seconds/play |

#### Exclusions

Same eligibility. Do not count ST as pace. Do not use skill position grades. Do not use the NFL UI pack `nfl-structural-pace-2026.ts`. Do not use CFB `pace = 1 + (skill−front_seven)/200`.

#### Mathematical definition

```text
ke.pace(team, game)     = n_scrimmage_off
ke.pace(team, week < W) = mean of team-game pace

ke.pace_competitive     = n_scrimmage_off with |score_diff| < D
  NFL D = 16 (proposed; must be audited — not copied silently if NFL script research uses another cut)
  CFB D = 16 (#555 warehouse competitive_margin; already owned)

ke.pace_seconds         = mean(−Δ game_seconds_remaining) on consecutive
                          offensive scrimmage snaps in the same drive
                          only if clock completeness passes
```

League reference (NFL live uses 62 plays/game) is a **display divisor**, not the rating. Publish plays/game first. `pace_index = plays / 62` is later.

CFB 2021–24 research mean was **66.14** plays / offense game. Do not force 62 onto CFB.

#### Opponent adjustment

**None in v1.** Pace vs opponent tempo is a matchup-stage problem. A two-way pace model is not specified.

#### Stabilization / sample

One completed eligible game is enough for a team-game. Season-to-date `THIN` if `n_games < 2`. Competitive pace `DATA_INSUFFICIENT` if score differential is missing on >5% of plays.

Seconds/play: if `game_seconds_remaining` / `TimeSecsRem` null rate > 2% on used plays → do **not** publish `ke.pace_seconds` (`DATA_INSUFFICIENT` for that companion). Plays/game still stands.

#### Prior / decay

No prior mixed into raw pace. Optional last-year plays/game stored beside, labeled prior.

#### Normalization / display

Native plays/game and (if certified) seconds/play. `1.00 = league` is display.

#### Point-in-time / cadence

Same as §7.1.

#### Validation test

Predict next-game offensive scrimmage-play count. Baselines: league mean, trailing mean. Residual vs game script (score state) is a **diagnostic**, not a reason to replace the rating with a coaching overlay (`game_script.py` is not KE Pace).

#### Failure behavior

Missing scrimmage tags → `DATA_INSUFFICIENT`. Skill−F7 / explosiveness-nudge pace → must not be emitted under this ID.

#### Buildability today

| NFL | **YES** for plays/game (already on the package as `/62`). **PARTIAL** for seconds/play (column exists; completeness not certified in this design). |
| CFB | **YES_RESEARCH** for plays/game and competitive pace (#555/#559). **PARTIAL** for seconds/play. Live compose pace is PROXY and must never keep this ID. |

---

### 7.5 KE Explosiveness

|                 |                                                                                           |
| --------------- | ----------------------------------------------------------------------------------------- |
| **ID**          | `ke.expl`                                                                                 |
| **Question**    | What share of eligible scrimmage plays are explosive, created and allowed, pass and rush? |
| **Layer**       | **DERIVED**                                                                               |
| **Native unit** | Rate (0–1)                                                                                |

Sport-specific knobs are **required**. Do not copy NFL 20/10 onto CFB to complete the schema.

#### Raw inputs

Yards and EPA already on owned PBP.

#### Exclusions

Same scrimmage filter. Missing yards **and** missing EPA → drop from denominator. One missing, one present: apply the sport rule below.

#### Mathematical definition

**NFL (reference knob set — already in tendency profiles, not KAV):**

```text
explosive_pass  ⇔ play_type = pass AND yards_gained ≥ 20
explosive_rush  ⇔ play_type = run  AND yards_gained ≥ 10
ke.expl_pass_*  = n_expl_pass / n_pass
ke.expl_rush_*  = n_expl_rush / n_rush
ke.expl_*       = (n_expl_pass + n_expl_rush) / n_scrimmage
```

KAV `yards_gained ≥ 12` (both) is a **different** estimator and stays off Layer-1. Situational ingest “pass ≥20 only” is an incomplete live subset — v1 requires the rush split. Missing rush split today is `PARTIAL` on live ingest, **not** a 0.085 fill.

**CFB (research knob set — #555, already owned):**

```text
explosive ⇔ EPA ≥ 1.0  OR  statYardage ≥ 15
pass/rush splits via `pass` / `rush` flags
```

These are Kos knobs, not a vendor iso-explosion. Do not relabel SP+ `expl_raw = 50 + 17*f(z_off)` as `ke.expl`.

Created = offense; allowed = opponent offense rate on plays faced.

#### Opponent adjustment

**None in v1.** #560 left explosiveness raw. A two-way explosion model is a later assignment.

#### Stabilization / sample

`THIN` if `n_pass < 40` or `n_rush < 40` for the split; omit the split rather than fill league 0.085. Combined rate `THIN` if `n_scrimmage < 80`.

#### Prior / decay

None inside the DERIVED rate. No `explosive_rate = 0.085` default inside `ke.expl`.

#### Normalization / display

Native rate. Later: vs league (NFL pass-league ~0.085 is an **anchor for display**, not a fill).

#### Point-in-time / cadence

Same as §7.1.

#### Validation test

Predict next-game explosive **rate** (and pass/rush splits). Baselines: league rate, trailing rate. Do not validate by totals MAE. Do not raise the yard threshold because #562 totals missed.

#### Failure behavior

| Only pass explosive available | `PARTIAL` (`ke.expl_pass` OK, `ke.expl_rush` `DATA_INSUFFICIENT`, `ke.expl` not published as if complete) |
| SP+ z heuristic | Must not use this ID |
| Missing rush yards | drop those rush plays; if rush-yards null rate > 1%, `PARTIAL` |

#### Buildability today

| NFL | **PARTIAL** — pass ≥20 is live; rush ≥10 exists in tendency code, **not** wired as Layer-1. Data available. Combined KE explosiveness is not implemented; it is buildable from owned PBP. |
| CFB | **YES_RESEARCH** raw (#555/#559). Warehouse `off_explosive_rate` is **dropped** at iterative adjust (EPA only). Live path is PROXY. |

---

### 7.6 KE Finishing Drives

|                 |                                                                                                 |
| --------------- | ----------------------------------------------------------------------------------------------- |
| **ID**          | `ke.finish`                                                                                     |
| **Question**    | When this offense reaches a scoring opportunity, how often and how many points does it produce? |
| **Layer**       | **DERIVED**                                                                                     |
| **Native unit** | Opportunity rate (0–1), points per opportunity (points), finish rate (0–1)                      |

v1 publishes a **bundle**, not a single unnamed 0–100. Primary reported number: **points per opportunity** (`ke.ppo`). Finish rate and opportunity rate are required siblings.

#### Raw inputs

| NFL                                                                                        | CFB                                                                               |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `fixed_drive` / `series` (043), `yardline_100`, `touchdown`, scoring play types, `posteam` | #555: `drive.id`, `start.yardsToEndzone`, `rz_play`, `type.text` points heuristic |

NFL player `red_zone.py` role shares are **not** finishing. They are player TD roles (PROXY relative to this rating).

#### Exclusions

Drives with no identified start. Games failing eligibility. Do not use RZ TD rate **alone** as `ke.finish`.

#### Mathematical definition

**Opportunity (shared concept, sport-specific yardstick):**

```text
NFL: drive reaches yardline_100 ≤ 40  OR  red-zone play (yardline_100 ≤ 20)
CFB: drive reaches start.yardsToEndzone ≤ 40  OR  truthy rz_play
     Red-zone subset: yardsToEndzone ≤ 20
```

Do not force NFL 40 onto CFB if a later audit wants 30 — CFB 40 is already owned (#555). Do not force CFB’s type.text points onto NFL if nflverse scoring plays are better.

**Points on drive:**

| NFL | Sum of official scoring results on the drive (TD 6 + XP/2pt if present, FG 3, safety 2). Prefer nflverse scoring flags over text. |
| CFB | #555 heuristic from `type.text` only: TD 6, Extra Point Good 1, two-point 2, FG Good 3, Safety 2. **No synthetic PAT if XP is missing.** Not official drive-result points. Must stay labeled `points_source=type_text_heuristic`. |

```text
ke.opp_rate  = n_opportunity_drives / n_drives
ke.ppo       = Σ points_on_opportunity / n_opportunity_drives
ke.finish    = share of opportunity drives with points_on_drive > 0
```

NFL live `red_zone_td_rate` vs 0.55 is a **partial** RZ diagnostic (`ke.rz_td`), not the finishing bundle.

#### Opponent adjustment

**None in v1.**

#### Stabilization / sample

`DATA_INSUFFICIENT` if `n_drives < 4` for a team-game opportunity rate. Season-to-date `THIN` if `n_opportunity < 8`. Do not fill PPO with 3.5.

#### Prior / decay

None inside the DERIVED rates.

#### Normalization / display

Native rates and points. CFB 2021–24 research: opp rate 0.456, PPO 3.51, finish 0.683 — **historical description**, not a fill.

#### Point-in-time / cadence

Same as §7.1.

#### Validation test

Predict next-game `ke.ppo` and `ke.finish`. Baseline: league PPO, trailing PPO. Secondary: red-zone TD rate. Do not use player TD shares.

#### Failure behavior

| NFL drive IDs missing | `DATA_INSUFFICIENT` for the bundle; `ke.rz_td` may still publish as `PARTIAL` if RZ plays exist |
| CFB missing `drive.id` | `DATA_INSUFFICIENT` |
| Using compose (none today) | n/a — live CFB finishing is MISSING; do not invent |

#### Buildability today

| NFL | **PARTIAL** — RZ TD rate live; full opportunity / PPO / finish **not** implemented. Drive/yardline columns exist (`fixed_drive`, `yardline_100`). Buildable from owned PBP once drive aggregation is specified in code (not this PR). |
| CFB | **YES_RESEARCH** raw (#555/#559). Warehouse `rz_epa_raw` stored, unwired. Live compose MISSING. Points heuristic must remain labeled. |

---

### 7.7 KE Havoc / Disruption

|                 |                                                                                         |
| --------------- | --------------------------------------------------------------------------------------- |
| **ID**          | `ke.havoc`                                                                              |
| **Question**    | On what share of opponent scrimmage plays does this defense produce a disruption event? |
| **Layer**       | **DERIVED** only after the event bundle is certified on the SoT                         |
| **Native unit** | Rate (0–1)                                                                              |

#### Canonical event set (definition first; columns second)

```text
havoc_event ⇔ tackle-for-loss  OR  forced fumble  OR  interception
optional_add: sack if TFL does not already include sacks (document overlap)
optional_add: pass breakup only if the column is certified
```

This is a written football definition. If the SoT cannot support TFL **and** FF **and** INT, **do not publish `ke.havoc`**. A smaller certified subset may publish as a **partial** with a different ID.

#### Raw inputs — honesty

| NFL normalized mart (`nfl_dp_play_by_play`) | Has `sack`, `qb_hit`, `interception`, `fumble`. **Does not** have `tackle_for_loss` or `fumble_forced`. |
| NFL raw payloads (`nfl_dp_raw_objects`) | Owned nflverse. Column inventory for TFL / FF is **not certified in this design**. Promote columns into the mart only after inventory. No PFF. |
| CFB core-31 (2014–2025 published list) | **No** sack / TFL / PBU / FF / INT flags. |
| CFB raw 2025/2026 | Flags `havoc`, `TFL`, `sack`, `int`, `pass_breakup`, `forced_fumble` **present** on later SDV copies. Completeness vs official charting **not certified**. `owned_metrics` left havoc out of scope. |

#### Allowed partial (must not use the `ke.havoc` ID)

| ID                        | Events                            | When allowed                                        |
| ------------------------- | --------------------------------- | --------------------------------------------------- |
| `ke.disruption_proxy_nfl` | `sack OR interception OR qb_hit`  | NFL mart only; **labeled proxy**                    |
| `ke.disruption_flags_cfb` | certified subset of 2025–26 flags | After null-rate audit; still not “official TFL/PBU” |

Pressure-in-backbone and OL `protection_index` are **not** havoc.

#### Exclusions

Same scrimmage. Do not count ST turnovers in `ke.havoc` unless a later ST-havoc note says so (v1: scrimmage only).

#### Mathematical definition (only if event set certified)

```text
ke.havoc_created(team) = n_havoc_events_by_defense / n_scrimmage_faced
ke.havoc_allowed(team) = n_havoc_events_against_offense / n_scrimmage_run
```

#### Opponent adjustment

**None in v1.**

#### Stabilization / sample

`THIN` below 80 snaps. No 50.

#### Prior / decay

None.

#### Normalization / display

Native rate.

#### Point-in-time / cadence

Same as §7.1, **after** certification.

#### Validation test

Predict next-game havoc rate vs league and trailing. If only the NFL proxy exists, validate **the proxy under its own ID** — do not report it as KE Havoc lift.

#### Failure behavior

Uncertified columns → `DATA_INSUFFICIENT` for `ke.havoc`. **Omit > impute.** Do not 50-fill. Do not buy PFF because flags failed.

#### Buildability today

| NFL | **NO** for named `ke.havoc`. **YES** for labeled `ke.disruption_proxy_nfl` from sack/INT/qb_hit. TFL/FF require a raw-column inventory (owned data, not a purchase). |
| CFB | **NO** for named `ke.havoc` until 2014–26 flag completeness is certified. 2026 flags are **PARTIAL / NEEDS_VALIDATION**. Historical core-31 cannot support it. |

---

### 7.8 KE Opponent-Adjusted EPA

|                 |                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------ |
| **ID**          | `ke.opp_adj_epa`                                                                                                   |
| **Question**    | What offensive and defensive EPA/play would this team produce against a league-average opponent?                   |
| **Layer**       | **ADJUSTED** in Phase 1 (PIT leave-one-out SOS). **MODELED** only if a fitted two-way is used (#560; not Phase 1). |
| **Native unit** | EPA/play. `off` higher better. `def` = EPA allowed, lower better.                                                  |

Phase 1 publishes this ID as **ADJUSTED** (deterministic PIT SOS). A fitted two-way remains **MODELED** and is **not** implemented here. It consumes `ke.off_eff` / `ke.def_eff` team-game `y`, not SP+, not identity.

Supporting metrics (pace, expl, finishing, havoc, ST) stay **unadjusted** until a sealed two-way exists for that metric.

#### Raw inputs

Team-game garbage-aware (CFB) or unweighted (NFL v1 default) EPA/play from §7.1–7.2, plus home flag, opponent identity, FBS/FCS flag (CFB), week, season.

#### Exclusions

§3.2–3.4. `n_games < 2` → do not treat the current-season posterior as full strength (`PRIOR_ONLY` or high `prior_weight`). FCS offenses may be kept with extra shrink (CFB); they are **not** in the FBS centering set.

#### Mathematical definition (canonical family)

```text
y_{g,i} = μ + h · home_{g,i} + off_i + def_j + ε
```

- `y` = team-game EPA/play on eligible scrimmage
- Identifiable baseline: league (NFL) or **FBS** (CFB) `off` and `def` centered at 0
- `μ` = intercept (league EPA/play)
- `h` = home-offense EPA/play. **Not a point spread.** Forbidden: `h × n_plays` as HFA points (#560 audit / #562).
- Joint estimation of `off` and `def` (ridge or iterated two-way). One SoT per sport.

**NFL today is not this estimator.** Live pieces:

| Stack                                                   | Class vs this spec                                                                                    |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `opponent_adjust_epa = raw − league`                    | PROXY center. Not full SOS. May remain a **diagnostic**.                                              |
| Past SOS `adj = raw + 0.70*(league_def − mean_opp_def)` | REAL_UNVALIDATED prior-side. Not the v1 SoT unless Ryan later promotes it.                            |
| KAV 12-iter                                             | REAL_UNVALIDATED. **Not** Layer-1 PR (desk forbids double-count). Not automatically `ke.opp_adj_epa`. |
| External DVOA hook                                      | PLACEHOLDER. Unused.                                                                                  |

v1 **design SoT** for NFL: the same additive two-way family as CFB, with NFL-specific λ / n0 / decay / no-FCS. **Not fitted in this PR.** Until a sealed NFL two-way exists, NFL may publish `ke.off_eff` / `ke.def_eff` and must label any center/SOS/KAV number as **that estimator**, not as `ke.opp_adj_epa`.

**CFB research candidate (#560, do not promote):**

```text
Estimator  fit_joint_v2_joint_mu_hfa_n0_ridge
λ = 40 · λ_fcs = 4λ · n0 = 4 · decay = 0.75 · 12 iters
selection  2023–2024 only
holdout    2025 MAE 0.1673 vs unadj 0.1911 vs blend 0.1837
production_promote = false
```

Warehouse 4-iter EPA is **legacy unused**. Do not run two CFB SoTs.

#### Opponent adjustment

This section **is** the opponent adjustment.

#### Stabilization / sample

|                  | NFL (proposed; not fitted)       | CFB (#560 frozen research)     |
| ---------------- | -------------------------------- | ------------------------------ |
| Shrink           | Sport-specific λ; do not copy 40 | λ=40 play-weight               |
| Game equivalents | Do not copy n0=4 without NFL val | n0=4                           |
| Thin             | `PRIOR_ONLY` if `n_games < 2`    | same; week-1 prior-only        |
| FCS              | n/a                              | λ_fcs=4λ; not in centering set |

#### Prior / decay

```text
prior_season_final → decay × that vector → week-1 book
current posterior mixes data + (λ + n0·ppg)·prior
```

| NFL | Last-year REG package is the natural prior. Decay **not copied** from 0.75. `games/8` is the **live product** blend onto indices — not this rating’s decay unless a later assignment equates them. |
| CFB | `decay=0.75` on season-final adj EPA. Week-1 = decayed prior only when `n_games < 2`. |

Vendor SP+ may be a **competing prior** (labeled vendor), never a fake measurement.

#### Normalization / display

Native EPA/play, FBS/NFL-centered at 0. `h` stays EPA/play. Season-final CFB `h` ~0.05–0.07; 2026 W1–2 `h≈0.244` is a **thin-window intercept**, not HFA points.

#### Point-in-time

Fit for week `W` of season `S` uses same-season games with `week < W` plus decayed prior. Leakage tests already exist for CFB warehouse (`week < W`).

#### Update cadence

After each eligible week cut. CFB research runners only until promote (not authorized here). NFL two-way: not scheduled by this spec.

#### Validation test

**Exactly the #560 family, per sport:** next-game O/D EPA MAE / RMSE / bias vs unadjusted STD and prior blend; early-season split; holdout year withheld from λ selection.

Do **not** validate `ke.opp_adj_epa` by spread MAE or totals MAE. Do not convert a good EPA book into a reopen.

#### Failure behavior

| Incomplete PBP | exclude game (CFB 84, not 85) |
| `n_games=0` | `PRIOR_ONLY` (decayed prior) or `DATA_INSUFFICIENT` if no prior |
| Thin-window `h` | publish `h` with `n` and window; do not score it |
| Two estimators disagree | pick one SoT; others diagnostic |

#### Buildability today

| NFL | **NO** as named `ke.opp_adj_epa` (two-way not sealed). **YES** to compute unadjusted EPA and to emit **labeled** center / SOS / KAV diagnostics from owned data. |
| CFB | **YES_RESEARCH** — #560 ADVANCE exists, sealed as next-game EPA, `production_promote=false`. **NO** as live KE / KEI / power. |

---

### 7.9 KE Overall / Team Strength

|                 |                                                                                     |
| --------------- | ----------------------------------------------------------------------------------- |
| **ID**          | `ke.team_strength`                                                                  |
| **Question**    | What is this team’s quality book, in native EPA, against a league-average opponent? |
| **Layer**       | **DERIVED from MODELED** (no new fit)                                               |
| **Native unit** | Net EPA/play                                                                        |

```text
ke.net_epa = ke.opp_adj_epa.off − ke.opp_adj_epa.def_allowed
```

v1 **does not** blend ST, pace, explosiveness, finishing, havoc, or identity into this number. Those ratings sit **beside** the book. Silent ST bleed (`0.5 * 0.065 * (st−1)` on the NFL backbone) is a live product mapping, not KE Overall.

If `ke.opp_adj_epa` is `DATA_INSUFFICIENT` / `PRIOR_ONLY`, team strength inherits that status. **Do not** fall back to SP+, returning production, or `power_index = 0.5*(off_100+def_100)`.

#### Raw inputs

Only `ke.opp_adj_epa` (and its `n`, `prior_weight`, `μ`, `h`).

#### Exclusions

If either side is missing → `DATA_INSUFFICIENT` (or `PRIOR_ONLY` if both sides are prior-only).

#### Mathematical definition

Net adj EPA/play as above. Optional published pair: `(off_adj, def_adj)` is the **full book**; net is the scalar.

Expected points vs an average opponent is **scoring projection** (downstream), not this rating. NFL Method B / True PR / CFB compose power are **live products**, not `ke.team_strength`.

#### Opponent adjustment

Already inside `ke.opp_adj_epa`. Do not adjust again. Do not add KAV on top.

#### Stabilization / sample

Inherit `n` / `prior_weight` / `THIN` from §7.8. No extra shrink.

#### Prior / decay

Inherit. Do not apply a second `games/8` on top of ridge n0.

#### Normalization / display

Native net EPA/play. Later: points-of-rating display, zero-center across the league. Tuesday α shrink (NFL Method B) is a **product publication** rule, not the engine identity.

#### Point-in-time / cadence

Same as §7.8.

#### Validation test

1. **Primary:** next-game `off_adj` / `def_adj` already validated in §7.8.
2. **Secondary (allowed, not construction):** next-game score margin and team points vs (a) net EPA × a **frozen** play-count, (b) unadjusted net EPA, (c) prior net. Margin and totals **separately**.
3. A failed totals check **does not** authorize retuning Off/Def/ST/Pace/Expl weights (#562 lock).

Do not use ATS / close as the seal.

#### Failure behavior

No adj book → no team strength. No SP+ backup. No 50. No `1.0` placeholder named KE.

#### Buildability today

| NFL | **NO** as named `ke.team_strength` until `ke.opp_adj_epa` exists. Live Method B / True PR / `TeamStrengthState` remain the **product** book and stay labeled as such. |
| CFB | **NO** as live KE. Research **net** of #560 `off−def` can be **derived** on the research table without being a power rating or a spread. |

---

## 8. Downstream boundaries (not v1 ratings)

| Stage               | May consume                                                        | Must not do in this track                                                           |
| ------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Matchup interaction | adj O vs adj D, pace as a **volume** input, bounded situation      | Re-use the same variance as a second unit boost; treat skill−F7 as pace             |
| Scoring projection  | A **frozen** conversion, eval’d on margin **and** total separately | New equation because #562 missed; `h_epa × plays` as HFA; retune explosiveness      |
| Market comparison   | Fair / KEI vs painted market **after** CoS CLEAR                   | Publish research EPA as KEI; reopen while flags are false; construct ratings on ROI |

NFL remat / overlay lock (#564 / #567) stays on its own track.

---

## 9. Shared names vs sport-specific knobs

| Topic                                     | Shared                       | Must differ                                                       |
| ----------------------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| Metric names / layer tags / failure codes | Yes                          | —                                                                 |
| EPA as the efficiency SoT                 | Yes                          | Vendor EPA column name kept (nflverse `epa` / SDV `EPA`)          |
| Success                                   | Concept                      | NFL nflverse `success` vs CFB `EPA_success` **and** 50/70/100     |
| Explosive knobs                           | Concept                      | NFL 20/10 vs CFB EPA≥1 or 15 yd                                   |
| Opportunity                               | Concept (≤40 yd)             | Points-on-drive source                                            |
| Pace                                      | Plays/offense-game           | League mean (62 vs ~66); competitive cut audited per sport        |
| Opp-adj family                            | `y = μ + h·home + off + def` | λ, n0, decay, FCS, garbage, OT                                    |
| Roster                                    | May prior                    | NFL injury/QB hook vs CFB portal/returning — never a fill for EPA |
| Early season                              | Label `prior_weight`         | NFL games/8 on the **product** index vs CFB n0/λ                  |

There is **no** shared football feature library today (#566). v1 does not create one in this PR. A future implementation may share infrastructure **after** this spec is accepted.

---

## 10. Buildability today (owned data only)

“Today” = this checkout’s owned sources and definitions, **without** new vendors, **without** treating HD-unmounted CFB as a byte-verified Railway store.

| ID                 | NFL                                 | CFB                            | Notes                                       |
| ------------------ | ----------------------------------- | ------------------------------ | ------------------------------------------- |
| `ke.off_eff`       | **YES**                             | **YES_RESEARCH**               | CFB needs worker volume for live            |
| `ke.def_eff`       | **YES**                             | **YES_RESEARCH**               | same                                        |
| `ke.st`            | **YES** (unvalidated module)        | **NO**                         | CFB omit                                    |
| `ke.pace`          | **YES** plays/game; seconds PARTIAL | **YES_RESEARCH**               | Live CFB pace is PROXY — do not keep the ID |
| `ke.expl`          | **PARTIAL** (rush split to wire)    | **YES_RESEARCH** raw           | Live CFB is synthetic                       |
| `ke.finish`        | **PARTIAL** (RZ only live)          | **YES_RESEARCH** raw           | NFL drive agg not built                     |
| `ke.havoc`         | **NO** (proxy only)                 | **NO**                         | Completeness first                          |
| `ke.opp_adj_epa`   | **NO** (diagnostics only)           | **YES_RESEARCH**               | Do not promote #560                         |
| `ke.team_strength` | **NO** (product PR ≠ KE)            | **NO** live; research net only | No SP+ fallback                             |

**Headline:** NFL can produce honest **measurement** today for Off, Def, ST EPA, and pace. CFB can produce honest **research measurement** today for Off, Def, pace, explosiveness, and finishing, plus a **research** two-way EPA. Neither sport can honestly emit a complete KE v1 **book** (adj EPA → team strength → scored market) from this spec without later assignments. That is not a purchase gap.

Proprietary KE estimate remains #556’s ~**28%**. This design does not pad it.

---

## 11. Ryan decision list (review, not work)

These are the calls this spec is asking for. Not implementation tickets.

1. **Accept native EPA/play** as KE Off/Def Efficiency (reject backbone composite and SP+ 0–100 as the identity).
2. **Keep two success columns** (`native` + `standard`) rather than forcing one cross-sport success.
3. **Accept sport-specific explosiveness knobs** (NFL 20/10, CFB EPA≥1 or 15).
4. **Omit CFB ST and both-sport named havoc** until certification. Allow NFL ST EPA as unvalidated DERIVED. Allow NFL disruption **proxy** under a different ID.
5. **Team strength = net adj EPA only** — no silent ST / identity / pace blend.
6. **#560 is the CFB MODELED candidate**, not live KE. Warehouse 4-iter stays legacy. NFL two-way is unspecified/unfitted.
7. **Scoring and boards stay out.** #562 stays REVISE. #561 stays dark.
8. If accepted, **next assignment** should be one stage: either NFL definition cleanup on measurement (rush expl, finishing bundle, ST validation, havoc column inventory) **or** CFB measurement-on-a-book (worker volume + raw mart, still `production_promote=false`). Not scoring. Not UI.

---

## 12. STOP

Authorized: Ryan reads this spec and the matrix.

**Not authorized by this document:**

- Any implementation or model fit
- Production or compose changes
- Promoting #559 / #560 / research net EPA
- A new scoring equation or loosening #562
- Board reopen / flag flips
- PFF or vendor shopping
- Unwiring SP+
- Relabeling identity as efficiency
- NFL remat from this PR
- Treating this folder as a live ratings engine

**STOP for Ryan review.**
