# KE Football v1 — metric / data / validation matrix

**Date:** 2026-09-15  
**Status:** `DESIGN_ONLY` · `production_promote=false`  
**Spec:** [`KE_FOOTBALL_V1_SPEC.md`](./KE_FOOTBALL_V1_SPEC.md)  
**Machine twin:** [`KE_FOOTBALL_V1_METRIC_MATRIX.json`](./KE_FOOTBALL_V1_METRIC_MATRIX.json)  
**Inventory:** [`KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md`](./KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md)

Nothing in this file implements a rating. It is the review grid for Ryan.

---

## Legend

### Layers

| Code    | Meaning                                                |
| ------- | ------------------------------------------------------ |
| RAW     | Observed play/game event or vendor column as published |
| DERIVED | Deterministic KE calculation from RAW                  |
| MODELED | Fitted / estimated                                     |

### Buildability today (owned data, no new vendors)

| Code           | Meaning                                                    |
| -------------- | ---------------------------------------------------------- |
| `YES`          | Owned data + complete definition; can compute now          |
| `YES_RESEARCH` | Can compute as a research artifact; not live / not promote |
| `PARTIAL`      | Some required pieces exist; others fail closed             |
| `NO`           | Required inputs missing or uncertified; omit               |

### Live vs research class (from #566; unchanged by this design)

`REAL_AND_VALIDATED` · `REAL_UNVALIDATED` · `PARTIAL` · `PROXY` · `PLACEHOLDER` · `CONSTANT_OR_50_FILL` · `DEAD_CODE` · `MISSING`

### Failure

Missing required information → `DATA_INSUFFICIENT` or a documented `PARTIAL`. No silent 50 / 1.0 / identity constant.

---

## 1. Rating × sport matrix

| ID                 | Name                     | Layer                | Native unit                 | NFL live today                                                      | CFB live today              | CFB research today             | NFL build today                | CFB build today  |
| ------------------ | ------------------------ | -------------------- | --------------------------- | ------------------------------------------------------------------- | --------------------------- | ------------------------------ | ------------------------------ | ---------------- |
| `ke.off_eff`       | Offensive Efficiency     | DERIVED              | EPA/play (↑ better)         | REAL_AND_VALIDATED EPA on spine; composite index is **not** this ID | PARTIAL vendor SP+ 0–100    | #559 raw EPA REAL_UNVALIDATED  | **YES**                        | **YES_RESEARCH** |
| `ke.def_eff`       | Defensive Efficiency     | DERIVED              | EPA/play allowed (↓ better) | same spine                                                          | PARTIAL SP+                 | same as off                    | **YES**                        | **YES_RESEARCH** |
| `ke.st`            | Special Teams Efficiency | DERIVED              | ST EPA/play                 | REAL_UNVALIDATED ST KAV; missing → 1.0 hook (**forbidden in v1**)   | PROXY unit 50 + 0.015 nudge | flags / types NEEDS_VALIDATION | **YES** (unvalidated)          | **NO**           |
| `ke.pace`          | Pace                     | DERIVED              | plays / offense-game        | PARTIAL (`/62`); UI pack PROXY                                      | PROXY skill−F7              | #555/#559 REAL_UNVALIDATED     | **YES** plays; seconds PARTIAL | **YES_RESEARCH** |
| `ke.expl`          | Explosiveness            | DERIVED              | rate                        | PARTIAL pass ≥20 only                                               | PROXY synthetic from SP+ z  | EPA≥1 or 15 yd raw             | **PARTIAL**                    | **YES_RESEARCH** |
| `ke.finish`        | Finishing Drives         | DERIVED              | PPO + finish + opp rate     | PARTIAL RZ TD only                                                  | MISSING                     | #555/#559 raw                  | **PARTIAL**                    | **YES_RESEARCH** |
| `ke.havoc`         | Havoc / Disruption       | DERIVED              | rate                        | PROXY pressure; TFL/FF not in mart                                  | MISSING (UI copy)           | 2026 flags uncertified         | **NO** (proxy ID only)         | **NO**           |
| `ke.opp_adj_epa`   | Opponent-Adjusted EPA    | MODELED              | EPA/play                    | PARTIAL (center + SOS + KAV ≠ one SoT)                              | PROXY vendor SP+            | #560 ADVANCE, not promote      | **NO**                         | **YES_RESEARCH** |
| `ke.team_strength` | Overall / Team Strength  | DERIVED from MODELED | net EPA/play                | REAL_AND_VALIDATED **product** PR — not this ID                     | REAL_UNVALIDATED compose    | #560 is not power              | **NO**                         | **NO** live      |

### Headline (do not pad)

|                             | NFL                                   | CFB                                         |
| --------------------------- | ------------------------------------- | ------------------------------------------- |
| Measurement buildable today | Off, Def, ST EPA, pace (plays)        | Off, Def, pace, expl, finish — **research** |
| Named havoc                 | No                                    | No                                          |
| Named opp-adj EPA           | No (diagnostics only)                 | Research only                               |
| Named team strength         | No (product PR stays labeled product) | No                                          |
| Purchase required           | **None**                              | **None**                                    |
| Platform (not vendor)       | —                                     | Worker-readable PBP copy                    |

~**28%** proprietary KE (#556) **unchanged**.

---

## 2. Data requirements (owned only)

| Asset                                      | Sport | Enough for which IDs?                                                                    | Gap if any                                           |
| ------------------------------------------ | ----- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `nfl_dp_play_by_play` + raw objects        | NFL   | `off_eff`, `def_eff`, `st`, `pace`, `expl` (data), `finish` (data), disruption **proxy** | TFL / FF not in normalized mart → `ke.havoc` blocked |
| `nfl_dp_team_situational_weekly` / rolling | NFL   | Current live EPA/success/pass-expl/RZ/pressure                                           | Rush expl + finishing bundle not first-class         |
| `nfl_dp_team_st_kav_weekly`                | NFL   | `ke.st` DERIVED                                                                          | Missing-ST `1.0` hook must not enter KE              |
| nflverse `game_seconds_remaining`          | NFL   | `ke.pace_seconds` if null-rate passes                                                    | Completeness not certified here                      |
| SDV PBP 2014–2025 HD lake                  | CFB   | Historical raw measurement                                                               | Unmounted here; Railway **no** parquet volume        |
| SDV 2026 `pbp_current` + schedule          | CFB   | W−1 raw; closed eligible **84**                                                          | Incomplete PBP fail-close (`401868140`)              |
| #555 `owned_metrics`                       | CFB   | Definitions for off/def/pace/expl/finish                                                 | Havoc/ST out of scope                                |
| #559 team-game table                       | CFB   | Unadjusted grain                                                                         | `opponent_adjusted=false`                            |
| #560 joint-ridge                           | CFB   | `ke.opp_adj_epa` research candidate                                                      | `production_promote=false`; EPA only                 |
| SP+ 2025 snapshot                          | CFB   | Vendor prior only                                                                        | Not a KE measurement                                 |
| CFBD / PPA / PFF                           | both  | Optional / forbidden                                                                     | Do not buy                                           |

### Eligibility (both sports)

Completed ∩ PBP-complete-to-official-final ∩ `week < W`. Score-only is not enough.

---

## 3. Per-rating construction card

Each row is the v1 contract. Native unit is the rating. Display index is later.

| ID                 | Inputs                          | Exclusions                           | Definition                                    | Opp adj        | Stabilize                                   | Prior / decay                              | Display              | PIT                | Cadence                      | First validation                                        | Failure                                       |
| ------------------ | ------------------------------- | ------------------------------------ | --------------------------------------------- | -------------- | ------------------------------------------- | ------------------------------------------ | -------------------- | ------------------ | ---------------------------- | ------------------------------------------------------- | --------------------------------------------- |
| `ke.off_eff`       | Scrimmage EPA created           | Incomplete PBP; non-finite EPA; ST   | `ΣEPA / n`                                    | none           | THIN `<80` plays; no mean fill              | none inside the number                     | EPA/play             | `week < W`         | per eligible game / week cut | next-game off EPA + success vs league & trailing        | `DATA_INSUFFICIENT` if n=0                    |
| `ke.def_eff`       | Scrimmage EPA allowed           | same                                 | `ΣEPA / n` faced                              | none           | same                                        | none                                       | EPA/play allowed     | same               | same                         | next-game EPA allowed                                   | same                                          |
| `ke.st`            | FG/XP/punt/KO EPA (NFL frame)   | non-ST; CFB uncertified              | `Σst_epa / n_st`                              | none in v1     | NFL THIN `<40` ST plays; no `1.0`           | `DATA_INSUFFICIENT` if n=0 (not 1.0)       | ST EPA/play          | W−1 join           | NFL weekly; CFB none         | next-game ST EPA (NFL only)                             | CFB omit                                      |
| `ke.pace`          | scrimmage count; optional clock | skill−F7; UI pack                    | plays/offense-game; competitive \|margin\|<16 | none           | THIN `<2` games; clock null>2% → no seconds | none                                       | plays/game           | same               | same                         | next-game play count                                    | no PROXY under this ID                        |
| `ke.expl`          | NFL 20/10; CFB EPA≥1 or 15 yd   | KAV≥12 as Layer-1; SP+ z             | pass/rush/combined rates                      | none           | omit split if n<40; no 0.085 fill           | none                                       | rate                 | same               | same                         | next-game expl rate — **not** totals                    | PARTIAL if rush missing                       |
| `ke.finish`        | drives + ≤40 yd + points        | player RZ shares; RZ-only as full ID | `ppo`, finish rate, opp rate                  | none           | THIN `<8` opportunities; no 3.5 fill        | none                                       | points / rates       | same               | same                         | next-game PPO / finish                                  | NFL bundle DATA_INSUFFICIENT without drives   |
| `ke.havoc`         | TFL ∧ FF ∧ INT certified        | uncertified flags; PFF               | events / snaps faced                          | none           | THIN `<80` snaps                            | none                                       | rate                 | after certify      | after certify                | next-game havoc **or** proxy-under-own-ID               | omit if uncertified                           |
| `ke.opp_adj_epa`   | team-game y, home, opponent     | OT on CFB modeled; incomplete PBP    | `y=μ+h·home+off+def`                          | **this is it** | NFL unfitted; CFB λ=40,n0=4                 | decayed season-final; NFL decay not copied | EPA/play, centered 0 | `week < W` + prior | weekly research / later      | next-game O/D EPA vs unadj & blend; holdout ≠ selection | PRIOR_ONLY or DATA_INSUFFICIENT; no `h×plays` |
| `ke.team_strength` | `off_adj − def_allowed`         | SP+ / identity / ST bleed            | net EPA/play                                  | already in adj | inherit                                     | inherit; no second games/8                 | net EPA/play         | inherit            | inherit                      | §7.8 primary; margin/points secondary, **separate**     | no book → no strength                         |

### Success companions (not a ninth engine rating)

| ID                    | Layer   | NFL                | CFB                     | Rule                                   |
| --------------------- | ------- | ------------------ | ----------------------- | -------------------------------------- |
| `ke.success_native`   | DERIVED | nflverse `success` | `EPA_success` ≡ `EPA>0` | Do not swap                            |
| `ke.success_standard` | DERIVED | audit vs nflverse  | 50/70/100               | Keep both; 2021–24 CFB agreement 0.940 |

### Allowed non-KE partials

| ID                        | Sport | Why it exists                   | Must not be named    |
| ------------------------- | ----- | ------------------------------- | -------------------- |
| `ke.disruption_proxy_nfl` | NFL   | sack ∨ INT ∨ qb_hit on the mart | `ke.havoc`           |
| `ke.disruption_flags_cfb` | CFB   | post-audit 2025–26 flags        | `ke.havoc`           |
| `ke.rz_td`                | NFL   | live RZ TD rate                 | `ke.finish`          |
| `ke.expl_pass`            | NFL   | live pass ≥20                   | `ke.expl` (complete) |

---

## 4. Validation matrix

Construction loss is **football**. ATS / close / ROI are forbidden as construction or as a reason to move knobs. #562 totals miss is **not** a reason to retune any row.

| ID                 | Primary target                           | Secondary (allowed)                     | Required baselines                     | Holdout rule              | Forbidden objective              |
| ------------------ | ---------------------------------------- | --------------------------------------- | -------------------------------------- | ------------------------- | -------------------------------- |
| `ke.off_eff`       | next-game off EPA/play, `success_native` | —                                       | league mean, trailing unadj            | chronological `week < W`  | ATS, totals                      |
| `ke.def_eff`       | next-game EPA allowed, success allowed   | —                                       | same                                   | same                      | ATS                              |
| `ke.st`            | next-game ST EPA/play                    | FG / punt / return splits               | league, trailing                       | NFL only until CFB exists | PFF grades, 1.0 hook error       |
| `ke.pace`          | next-game off scrimmage count            | competitive count; seconds if certified | league, trailing                       | same                      | coaching overlay fit             |
| `ke.expl`          | next-game expl rate + splits             | —                                       | league rate, trailing                  | same                      | totals MAE (#562)                |
| `ke.finish`        | next-game PPO, finish rate               | RZ TD                                   | league PPO, trailing                   | same                      | player TD-share                  |
| `ke.havoc`         | next-game havoc rate                     | proxy rate under proxy ID               | league, trailing                       | after certify             | “flags exist”                    |
| `ke.opp_adj_epa`   | next-game O/D EPA                        | early-season W1–4                       | unadj STD, prior blend                 | selection years ≠ holdout | spread MAE, `h` as points        |
| `ke.team_strength` | inherits adj EPA tests                   | margin **and** points **separately**    | net unadj, prior net, frozen plays×EPA | same                      | ATS / close / retune from totals |

Also required on every published rating: stability vs `n`, calibration by decile, visible `prior_weight`.

---

## 5. What must never occupy a KE cell

| Thing                                                                     | Why                               |
| ------------------------------------------------------------------------- | --------------------------------- |
| CFB live success / explosiveness / skill−F7 pace                          | PROXY / synthetic                 |
| CFB `/pro/cfb/tempo` and havoc card                                       | PLACEHOLDER / pending             |
| Returning production, portal, recruiting, unit grades, coaching constants | Identity, not measurement         |
| Six snapshot `league_average_fill=50` rows                                | CONSTANT_OR_50_FILL               |
| NFL `st_index=1.0` / `placeholder_league_avg`                             | CONSTANT_OR_50_FILL               |
| #560 EPA as a spread or KEI                                               | Research ADVANCE                  |
| #562 points as house scoring                                              | REVISE (totals failed)            |
| NFL KAV as second Model PR                                                | Desk forbids double-count         |
| NFL structural-pace UI pack                                               | PROXY                             |
| Player-production / fantasy spine                                         | Different engine                  |
| PFF / CFBD PPA                                                            | Not owned / optional / do not buy |

---

## 6. Architecture mapping (today vs v1 target)

| Stage         | NFL now                                  | CFB live now              | CFB research now                     | v1 target                             |
| ------------- | ---------------------------------------- | ------------------------- | ------------------------------------ | ------------------------------------- |
| Data truth    | nflverse + `nfl_dp_*`                    | SP+ HTML; PBP unused      | SDV lake + versioned 2026; 84 closed | One SoT/sport + SHA + fail-closed PBP |
| Measurement   | EPA/success/pass-expl/RZ/pressure/ST     | Synthetic + identity pace | Raw team-game                        | §7.1–7.7 native units                 |
| Opp adj       | Center + SOS + KAV split                 | Vendor SP+                | #560 EPA only                        | One two-way SoT/sport                 |
| Team strength | `TeamStrengthState` / Method B / True PR | Compose 0–100             | adj table ≠ PR                       | net adj EPA                           |
| Matchup       | off/def ratio + response                 | `(off/def)^1.40` + units  | not KE                               | boundary                              |
| Scoring       | `expected_team_points` (remat separate)  | same family               | #562 REVISE                          | boundary; do not retune               |
| Market        | KEI dark                                 | KEI dark                  | none                                 | last; still dark                      |

---

## 7. STOP

Docs only. No fit. No promote. No board. No PFF.

Next action: Ryan review of [`KE_FOOTBALL_V1_SPEC.md`](./KE_FOOTBALL_V1_SPEC.md) §11 decision list.
