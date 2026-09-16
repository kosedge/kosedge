# KE Football — gap matrix, data requirements, proposed architecture

**Date:** 2026-09-15  
**Inventory:** [`KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md`](./KE_FOOTBALL_RATINGS_ENGINE_INVENTORY_2026-09-15.md)  
**Extends:** [#556](https://github.com/kosedge/kosedge/pull/556) football cells · [#558](https://github.com/kosedge/kosedge/pull/558) matrix · CFB [#555](https://github.com/kosedge/kosedge/pull/555)/[#559](https://github.com/kosedge/kosedge/pull/559)/[#560](https://github.com/kosedge/kosedge/pull/560)/[#562](https://github.com/kosedge/kosedge/pull/562)

**This file is still inventory / research.** No implementation. No model fit. No new scoring equation. No board reopen. No PFF.

#562 lock (visible): CFB efficiency → scoring is **REVISE**. Margin improved (−8.5% vs prior-points blend). Totals **missed** (+3.4% vs train league mean). Do not loosen the gate. Do not invent a replacement equation. NFL remediation is a **separate** track.

---

## 0. How to read a cell

Each concept has **three marks**, same scheme as #558, updated after later PRs:

1. **Live-path class** — what the customer-facing compose / Layer-1 actually uses today (even if boards are dark).
2. **Research-path class** — what exists off to the side (warehouse, #555–#562). `n/a` if none.
3. **Data / metric** — `DATA_AVAILABLE` vs `DATA_MISSING`; `IMPLEMENTED_VALIDATED` / `NEEDS_IMPLEMENTATION` / `NEEDS_VALIDATION`.

Rules carried forward:

- Opponent-adjusted KE is an implementation/validation problem, **not** an external-data gap.
- PPA is **optional**. Missing PPA ≠ buy CFBD or PFF.
- Havoc / ST: field-completeness first.
- Synthetic SP+ success / explosiveness / skill−F7 pace are **PROXY**, never “measured.”
- Returning production / unit grades / coaching constants are **not** KE football features.

---

## 1. Gap matrix — NFL vs CFB

Live class is the #556/#558 live class unless a later PR changed the **live** path (none did). Research class is new.

| KE concept                              | NFL live                                          | NFL research / side       | CFB live                                         | CFB research                                                       | NFL data / metric                                  | CFB data / metric                                                                                                   |
| --------------------------------------- | ------------------------------------------------- | ------------------------- | ------------------------------------------------ | ------------------------------------------------------------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Offensive efficiency                    | **REAL_AND_VALIDATED**                            | same spine                | **PARTIAL** (SP+ 0–100)                          | #560 adj EPA **REAL_UNVALIDATED**; warehouse 4-iter unused         | DATA_AVAILABLE / IMPLEMENTED_VALIDATED             | DATA*AVAILABLE / live NEEDS_IMPLEMENTATION; research EPA NEEDS_VALIDATION \_as ratings* (sealed _as EPA predictor_) |
| Defensive efficiency                    | **REAL_AND_VALIDATED**                            | same                      | **PARTIAL**                                      | same as off                                                        | same                                               | same                                                                                                                |
| Special teams                           | **REAL_UNVALIDATED**                              | ST KAV 2013–25            | **PROXY** (unit 50 + 0.015 nudge; SP+ ST unused) | flags / types **NEEDS_VALIDATION**                                 | DATA_AVAILABLE / NEEDS_VALIDATION                  | DATA_AVAILABLE / NEEDS_VALIDATION                                                                                   |
| Pace                                    | **PARTIAL** (plays/62)                            | UI pack PROXY             | **PROXY** (skill−F7 + expl/400)                  | #555/#559 plays/game **REAL_UNVALIDATED**                          | DATA_AVAILABLE / NEEDS_VALIDATION                  | DATA_AVAILABLE / live NEEDS_IMPLEMENTATION; research implemented raw                                                |
| Explosiveness                           | **PARTIAL** (pass ≥20 only)                       | KAV ≥12; tendencies 10/20 | **PROXY** (**synthetic** from SP+ z)             | EPA≥1 or yds≥15 **REAL_UNVALIDATED** raw; warehouse dropped at adj | DATA_AVAILABLE / NEEDS_IMPLEMENTATION (rush split) | DATA_AVAILABLE / live is PROXY — do not promote the z-heuristic                                                     |
| Finishing                               | **PARTIAL** (RZ TD rate)                          | player RZ shares PROXY    | **MISSING** / warehouse RZ **DEAD_CODE**         | #555/#559 opp / PPO / finish **REAL_UNVALIDATED**                  | DATA_AVAILABLE / NEEDS_VALIDATION                  | DATA_AVAILABLE / NEEDS_IMPLEMENTATION (live)                                                                        |
| Havoc / disruption                      | **PROXY** (pressure)                              | sack rates                | **MISSING** (UI copy)                            | 2026 flags present; stuff_rate unwired                             | DATA_AVAILABLE / NEEDS_IMPLEMENTATION              | DATA_AVAILABLE / NEEDS_VALIDATION                                                                                   |
| EPA                                     | **REAL_AND_VALIDATED**                            | —                         | **MISSING** on live                              | Raw + #560 adj **REAL_UNVALIDATED**                                | DATA_AVAILABLE / IMPLEMENTED_VALIDATED             | DATA_AVAILABLE / live NEEDS_IMPLEMENTATION                                                                          |
| PPA                                     | **MISSING** (optional)                            | —                         | **MISSING** (optional)                           | **MISSING** (optional)                                             | DATA_MISSING optional                              | DATA_MISSING optional                                                                                               |
| Opponent adjustment                     | **PARTIAL** (center + SOS + KAV≠PR)               | —                         | **PROXY** (vendor SP+)                           | #560 **ADVANCE** as EPA; warehouse 4-iter unused                   | DATA_AVAILABLE / NEEDS_VALIDATION                  | DATA_AVAILABLE / live NEEDS_IMPLEMENTATION                                                                          |
| SOS                                     | **REAL_UNVALIDATED**                              | projected outlook         | **PARTIAL** (implicit)                           | implicit in two-way                                                | DATA_AVAILABLE / NEEDS_VALIDATION                  | DATA_AVAILABLE / NEEDS_IMPLEMENTATION                                                                               |
| Power ratings                           | **REAL_AND_VALIDATED** (compute; UI dark)         | —                         | **REAL_UNVALIDATED** (compose SoT)               | #560 is **not** power                                              | DATA_AVAILABLE / IMPLEMENTED_VALIDATED             | DATA_AVAILABLE / NEEDS_VALIDATION                                                                                   |
| Team strength                           | **REAL_AND_VALIDATED**                            | —                         | **REAL_UNVALIDATED**                             | —                                                                  | same                                               | same                                                                                                                |
| Scoring projection                      | REAL_UNVALIDATED (Layer-1 `expected_team_points`) | —                         | REAL_UNVALIDATED (compose)                       | #562 **REVISE** (totals fail)                                      | NFL remediations **separate track**                | **Do not invent a new equation**                                                                                    |
| Returning production / units / coaching | NFL continuity PROXY (curated)                    | QB premium PARTIAL        | **PROXY / CONSTANT_OR_50_FILL**                  | n/a as efficiency                                                  | Not a KE feature                                   | **Not a KE feature**                                                                                                |

### Headline gaps (do not pad)

| Gap                                           | NFL                          | CFB                                                            |
| --------------------------------------------- | ---------------------------- | -------------------------------------------------------------- |
| Owned play-level O/D on the **live** path     | Present (v1.1)               | **Absent** — live is vendor SP+                                |
| Measured pace on live path                    | Present (plays/62)           | **Absent** — identity heuristic                                |
| Measured explosiveness on live path           | Pass only                    | **Absent** — SP+ z synthetic                                   |
| Named havoc                                   | Absent (pressure proxy)      | Absent (UI + unverified flags)                                 |
| ST as a real module                           | Present, unvalidated         | Absent (50 + 0.015)                                            |
| Opponent-adj **owned** estimator on live path | Partial (center; KAV not PR) | **Absent** (#560 research only)                                |
| Current-season rolling form                   | Weekly nflverse              | Research #559 raw; not compose                                 |
| Persistence that a worker can see             | Postgres `nfl_dp_*`          | HD lake often unmounted; Railway has **no** CFB parquet volume |
| Scoring that beats Vegas-free totals          | Separate NFL track           | #562 **failed totals** — stop                                  |

**Proprietary KE Football estimate:** still the #556 ~**28%** overall / ~**64%** of NFL cells / ~**34%** of CFB **live** cells. Counting #560 as “KE built” would pad. Research EPA is real; it is not the engine.

---

## 2. Data requirements for a real KE football feature layer

This is a **requirements list**, not a purchase list and not a build ticket.

### 2.1 Already owned (do not re-acquire)

| Asset                                    | Sport | Status                                                                   | Enough for a feature layer?                                                                                                                     |
| ---------------------------------------- | ----- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| nflverse PBP + `nfl_dp_*` marts          | NFL   | Live ingest                                                              | **Yes** for measurement. Gaps are definition consistency (explosive yards) and wiring (rush explosive, havoc, ST validation), not a new vendor. |
| SportsDataverse `espn_cfb_pbp` 2014–2025 | CFB   | Canonical HD `raw/cfb/pbp/` (do not overwrite). Repo/Railway often empty | **Yes historically** if HD (or a worker copy) is present. Inventories exist; this checkout does not byte-verify the lake.                       |
| SDV 2026 current PBP + schedule          | CFB   | Versioned `pbp_current/as_of_YYYYMMDD/`                                  | **Yes for W−1 raw.** Eligibility = actually completed ∩ PBP ∩ `week < W`. Incomplete PBP fail-closed.                                           |
| #555 metric definitions                  | CFB   | Code + tests                                                             | Success/EPA/pace/expl/finishing **definitions** exist.                                                                                          |
| #559 team-game table                     | CFB   | Research artifact                                                        | Raw unadjusted grain exists for 2026 (closed 84 after #560).                                                                                    |
| #560 adj EPA                             | CFB   | Merged research                                                          | Owned two-way for **EPA/play only**. Not ST, pace, expl, havoc.                                                                                 |
| SP+ 2025 snapshot                        | CFB   | Live compose SoT                                                         | Vendor prior. Keep labeled vendor. Not a KE measurement.                                                                                        |
| CFBD API                                 | CFB   | Key name on Railway; 401 without Ryan’s account                          | **Not required** for the feature layer if SDV EPA is the SoT. Soft-parked.                                                                      |
| PPA                                      | both  | Absent                                                                   | Optional. Default: build around EPA.                                                                                                            |
| PFF                                      | both  | Absent                                                                   | **Do not purchase.**                                                                                                                            |

### 2.2 Required to _be_ a feature layer (still no implementation)

**Data truth**

1. **One play-level SoT per sport** with SHA, as_of, and eligibility rules. NFL: nflverse week-capped. CFB: SDV historical lake + versioned current; never mix a Q2 cut with a final.
2. **Completed-game gate** (CFB already learned this): status + score is not enough; PBP must reach the official final. NFL already gates on schedule scores — keep that honesty.
3. **A place the model can read.** NFL already has Postgres. CFB research files on a laptop HD are not a production feature store. Copy/core parquet + checksums to a worker volume or object store is a **platform** requirement, not a vendor requirement. Do not mount the Mac into Railway.
4. **Identity spine** that does not 50-fill official teams. NFL product aliases (`LA`→`LAR`). CFB official FBS hard-fail (keep).

**Football measurement (raw, unadjusted, inspectable)**

Minimum columns, both sports, team-game and team-week (`week < W`):

| Feature                                            | NFL source today   | CFB source today                                                        | Requirement                                                |
| -------------------------------------------------- | ------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| EPA/play created / allowed                         | situational        | #555/#559                                                               | Keep vendor EPA name; do not invent KE-EP                  |
| Success created / allowed                          | nflverse `success` | `EPA_success=EPA>0` **and** standard 50/70/100 as a **separate** column | Document which one is “KE success”; do not silently swap   |
| Explosiveness created / allowed, **pass and rush** | pass ≥20 only      | EPA≥1 or 15 yd                                                          | One documented knob set per sport (they may differ)        |
| Pace (plays/offense-game) + competitive pace       | plays/62           | #555 defs                                                               | Live CFB must stop using skill−F7 if this layer is adopted |
| Finishing (opportunity, PPO, finish rate, RZ)      | RZ TD only         | #555/#559                                                               | Opportunity definition must be stated (CFB: ≤40 yd)        |
| ST (FG / punt / return EPA or KAV)                 | ST KAV             | types/flags only                                                        | Completeness audit before any ST rating                    |
| Havoc / disruption                                 | pressure / sacks   | flags + stuff                                                           | Completeness vs a written definition; no silent 50         |

Garbage / blowout weights belong in measurement notes, not hidden in a z-score.

**What must not be stored as “efficiency”**

- Returning snap/start, portal in/out, recruiting, experience
- QB class multipliers
- Curated new-HC / OC / DC flags
- SP+ z → fake success / explosiveness
- League 50 fills for official FBS

Those may remain **priors / identity** (CFB especially). They are a different layer.

**Opponent adjustment**

- Target **O/D EPA/play first** (what #560 already is for CFB; what NFL backbone+KAV partially is).
- Supporting metrics (pace, expl, finishing, havoc, ST) stay raw until a sealed two-way exists for that metric — #560 already states this.
- PIT: same-season `week < W` + decayed prior. FCS / cupcake handling is sport-specific (CFB `λ_fcs`; NFL SOS dampen 0.70).
- Do not convert a thin-window home EPA intercept into points.

**Stabilization / priors (allowed to differ)**

| Knob             | NFL today                                          | CFB today                               | Feature-layer rule                                                 |
| ---------------- | -------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------ |
| Current vs prior | `games/8`                                          | #560 `n0=4`, `decay=0.75`               | Sport-specific; freeze before eval                                 |
| Shrink           | variance shrink on additives                       | `λ=40`, `λ_fcs=4λ`                      | Sport-specific                                                     |
| Roster treatment | Injury overlay on current indices; QB premium hook | Returning/portal/QB **compose weights** | Roster may **prior** a rating; it must not **replace** measurement |
| Early season     | games 0–2 prior-heavy                              | week-1 prior-only if `n_games<2`        | Label prior_weight; no silent 50                                   |

**Out of scope for the feature layer (downstream)**

- Matchup `^response` / unit boosts
- Scoring projection (`expected_team_points`, #562 `a+b*epa*plays`)
- KEI / market / Edge Board
- PLAY tags

#562 already showed: a decent EPA book can still **lose** a totals gate. That is a scoring-layer problem, not a reason to fake explosiveness.

### 2.3 Smallest remaining _external_ need

**None that require a purchase.**

| Temptation                               | Verdict                                                                        |
| ---------------------------------------- | ------------------------------------------------------------------------------ |
| PFF grades                               | **No.** Not in this track.                                                     |
| CFBD PPA                                 | Optional. SDV EPA is sufficient to define the layer.                           |
| New historical vendor                    | Owned 2014–2025 SDV claim stands on inventory; verify HD/copy, do not re-shop. |
| Charted havoc if flags fail completeness | Then havoc stays out of the layer. Omit > impute.                              |

---

## 3. Proposed canonical KE Football feature layer

**Proposed for Ryan review. Not authorized to build. Not a scoring equation. Not a board plan.**

Shared **conceptually** between NFL and CFB. Different priors, opponent adjustment, roster treatment, and stabilization — by design.

```text
                    ┌─────────────────────────────────────────────┐
                    │           KE FOOTBALL FEATURE LAYER         │
                    │         (measurement + adj + book)          │
                    └─────────────────────────────────────────────┘
                                      │
  data truth → football measurement → opponent adjustment → team strength
           → matchup interaction → scoring projection → market comparison
```

### 3.1 Layer contracts

| Layer                    | Question                                     | Allowed inputs                                                         | Forbidden                                                                                                 |
| ------------------------ | -------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Data truth**           | What plays/games exist, as of when?          | PBP + schedule + identity + SHA + eligibility                          | DELAYED leftovers; future weeks; silent 50 for official teams                                             |
| **Football measurement** | What happened on those plays?                | EPA, success, expl, pace, finishing, ST, havoc — **raw**, labeled defs | SP+ z proxies; roster/coaching constants renamed as “explosiveness”                                       |
| **Opponent adjustment**  | How good was that vs the opponent that week? | Two-way / SOS on **measurement** targets                               | Using vendor SP+ as if it were owned adj; double-counting KAV + backbone + SOS into one PR without a rule |
| **Team strength**        | What is the team’s quality book?             | Stabilized adj O/D (+ optional ST) + inspectable uncertainty           | Identity stack substituting for missing measurement on the live path                                      |
| **Matchup interaction**  | What happens when two books meet?            | O vs D, pace interaction, bounded situation                            | Re-using the same variance as a second “unit boost” without ablation                                      |
| **Scoring projection**   | What score follows?                          | A **frozen** conversion, eval’d on margin **and** total separately     | A new equation because #562 missed totals; converting `h_epa` × plays                                     |
| **Market comparison**    | Where is the house vs the board?             | Fair / KEI vs painted market                                           | Publishing research EPA as KEI; reopening while flags are false                                           |

NFL today is strongest at **measurement → team strength**, weaker at a single opponent-adj SoT, and has a separate scoring/remediation track.

CFB live is strongest at **identity compose + vendor strength**, weakest at **measurement**. CFB research is now strongest at **measurement + O/D EPA adj**, and has a **failed** scoring conversion.

### 3.2 Canonical feature list (names only — no weights)

Shared names. Sport-specific estimators sit behind the name.

| Feature id                          | Meaning                          | NFL prior                                    | CFB prior                                                                 |
| ----------------------------------- | -------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------- |
| `ke.off_epa`                        | Adj offensive EPA/play           | Backbone off EPA (league-centered) / KAV off | #560 `off_i` (research)                                                   |
| `ke.def_epa`                        | Adj defensive EPA/play (allowed) | Backbone def EPA                             | #560 `def_j` (research)                                                   |
| `ke.success_off` / `ke.success_def` | Success created / allowed        | nflverse success                             | `EPA_success` **or** standard SR — pick one, keep the other as diagnostic |
| `ke.expl_pass_*` / `ke.expl_rush_*` | Explosive created / allowed      | Pass ≥20 exists; rush **to build**           | EPA≥1 or 15 yd exists raw                                                 |
| `ke.pace`                           | Plays / offense game vs league   | `/62`                                        | #555 plays/game (not skill−F7)                                            |
| `ke.pace_competitive`               | Same, competitive snaps          | not first-class                              | `\|margin\|<16` exists raw                                                |
| `ke.finish`                         | Opportunity conversion / PPO     | RZ TD partial                                | #555 finish / PPO raw                                                     |
| `ke.st`                             | Special teams EPA or KAV         | ST KAV                                       | **omit until validated**                                                  |
| `ke.havoc`                          | Disruption created / allowed     | **omit or keep as pressure_proxy labeled**   | **omit until flags validated**                                            |
| `ke.sos`                            | Derived from opponent book       | Past SOS 0.70 dampen                         | Implicit in #560; optional export                                         |
| `ke.n` / `ke.prior_weight`          | Sample + shrink                  | games/8                                      | n0/λ/decay                                                                |
| `ke.identity_*`                     | Roster / QB / coach              | injury / QB premium / continuity             | returning / portal / QB class / staff                                     |

`ke.identity_*` is **visible** and **not** a substitute for `ke.off_epa`.

### 3.3 What each sport is allowed to do differently

| Topic         | NFL                                                                            | CFB                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Prior         | Last-year REG package                                                          | Decayed season-final adj EPA + (optional) labeled vendor SP+ as a **competing prior**, never as fake success                         |
| Opp adj       | May keep KAV off Layer-1 or promote one estimator — **Ryan call, not this PR** | #560 is the research candidate; warehouse 4-iter is legacy unused                                                                    |
| Roster        | Injury overlay on **current** indices                                          | Portal/returning as **prior mix**, early-season only, labeled approximate                                                            |
| Stabilization | games/8, clamps 0.82–1.24                                                      | λ/n0/FCS, wider uncertainty W1–W4                                                                                                    |
| Scoring       | Existing `expected_team_points` — remediation **separate**                     | #562 form is **frozen-failed** on totals. Next scoring work, if any, is a new assignment after this review — not a silent `a,b` grid |
| Market        | Dark until NFL gates CLEAR                                                     | Dark until CFB gates CLEAR. Spreads ≠ totals                                                                                         |

### 3.4 Honesty rules if this layer is ever built

1. Live CFB `success_*` / `explosiveness` / pace must be **renamed or replaced**. They cannot keep those names if they remain SP+ z / skill−F7.
2. #560 may be cited as **research adj EPA**, never as “KE Ratings live.”
3. #562 may be cited as **REVISE**, never as the house scoring model.
4. Havoc/ST stay off the board until completeness + a definition beat “flags exist.”
5. No 50-fill for official FBS. No PFF-shaped holes.
6. Boards stay dark. `production_promote` stays false until CoS CLEAR per sport **and** market.

---

## 4. Mapping today’s artifacts onto the target spine

| Target stage         | NFL now                                  | CFB live now                              | CFB research now                              |
| -------------------- | ---------------------------------------- | ----------------------------------------- | --------------------------------------------- |
| Data truth           | nflverse + `nfl_dp_*`                    | SP+ HTML snapshot; PBP unused             | SDV lake + versioned 2026; eligibility closed |
| Football measurement | EPA/success/pass-expl/RZ/pressure/ST     | **Synthetic** success/expl; identity pace | Raw team-game (#555/#559)                     |
| Opponent adjustment  | Center + SOS + KAV (split)               | Vendor SP+                                | #560 ADVANCE (EPA only)                       |
| Team strength        | `TeamStrengthState` / Method B / True PR | Compose indices / power SoT               | 2026 adj table (not PR)                       |
| Matchup interaction  | `off/def` ratio + week response          | `(off/def)^1.40` + unit boosts + coach    | not built as KE                               |
| Scoring projection   | `expected_team_points`                   | same family, different PPG/HFA            | #562 REVISE                                   |
| Market comparison    | KEI vs book (dark)                       | KEI vs book (dark)                        | none                                          |

The missing KE work is **not** “write a new total.” It is: make **measurement** real on CFB live (or keep live vendor-labeled), keep NFL measurement honest, and only then talk about a shared strength book. Scoring stays downstream and separately gated.

---

## 5. STOP — Ryan review

**Authorized here:** read the inventory, the matrix, and this architecture.

**Not authorized:**

- Production or compose changes
- Model fitting or a new scoring equation
- Loosening #562 totals
- Board reopen / flag flips
- PFF or vendor shopping
- Promoting #560 or #559 onto KEI
- Unwiring SP+
- Relabeling returning production / units / coaching as KE efficiency
- Starting NFL remediation from this PR

If Ryan accepts the layer, the **next** assignment should say which stage is in scope (almost certainly CFB measurement-on-a-book vs NFL definition cleanup — not scoring, not boards). Until then, this track is **stopped**.

---

_End. 2026-09-15._
