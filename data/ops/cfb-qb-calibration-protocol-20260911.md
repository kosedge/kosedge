# CFB QB calibration dataset + validation protocol

**Date:** 2026-09-11  
**Branch:** `cursor/cfb-qb-cal-protocol-1bf8`  
**Kill switch:** ON. No PLAY. No public CFB. No λ. No Line Curve.  
**Production math:** frozen. `MATCHUP_RESPONSE` stays **1.40**. No median→50 ship.

#539 diagnosis is accepted: hist-cal trained downstream knobs on
`unknown @ qb_talent 50` (index ≈ 0.92). Live 2026 serves prior-year
counting-stat talent centered near **67** (index ≈ 1.20). The next
question is not “what coefficient fixes CFB?” It is:

> Can we construct a legitimate historical dataset containing the
> feature we are now serving?

This document answers that, then stops. It does not recalibrate.

Companion JSON: `data/ops/cfb-qb-calibration-protocol-20260911.json`  
Contract module: `src.services.cfb_season_engine.qb_feature_contract`  
Version: **`cfb-qb-feature-v1`**

---

## Recommendation

| Decision | Call |
|---|---|
| **Build the historical dataset?** | **GO** (Layer A now; Layer B blocked) |
| **Recalibrate MATCHUP_RESPONSE / QB weights now?** | **STOP** |
| **Need a different QB architecture?** | **Not yet.** The live talent definition is historically reconstructable. |
| **2026 W1/W2 role** | Confirmatory only. Not a fitting target. |
| **2025 residuals** | **Sealed** unless a later note explicitly unseals them. |

**Why GO on the dataset.** The feature that caused the skew is prior-year
`attempts / yards / TDs` run through `talent_from_qb_stats`, plus class
from attempts / portal / room. Those inputs exist as year-scoped ESPN
core artifacts:

- Membership: `seasons/{Y}/teams/{id}/athletes` (year-locked; ALA counts
  2022=236, 2023=242, 2024=182, 2025=177, 2026=127).
- Counting stats: `seasons/{Y}/types/2/athletes/{id}/statistics`
  (Kyle McCord probe: 2023 = 348/3170/24, 2024 = 558/4326/29, 2025 = 404).
- Portal: Y vs Y−1 roster-team join (McCord 194 → 183 between 2023 and 2024).

Using the completed **prior** season as Week-0 of season Y is legal. It
is what 2026 W1/W2 already serve (2025 totals, frozen through W2).

**Why STOP on coefficients.** There is no v1 historical universe yet.
Fitting 1.40 again on placeholder@50 would repeat the failure. Fitting
against 2026 W1/W2 would make the confirmatory slate the training target.

**Why not a new architecture.** We do not need a different QB *definition*
to get a reproducible history. We need to *build* the live definition
backward. If Layer A coverage fails the gates below, revisit architecture
then — not now.

---

## 1. Canonical QB feature contract (`cfb-qb-feature-v1`)

Serve writer today: `scripts/cfb/package_real_roster_2026.py`.
Locked spec: `qb_feature_contract.py`. Tests require them to match.
Downstream index (`qb_situation.py`) is unchanged and is **not** part of
the feature rewrite — it consumes v1 inputs.

### 1.1 Talent formula (exact)

No completion-rate term. Caps almost never bind on 2026 FBS.

```text
if att <= 0:
    talent = 48.0                  # 52.0 if is_portal
else:
    ypa = yards / att
    talent = clamp(
        42
        + min(22, att / 22)        # saturates at 484 attempts
        + min(12, ypa * 1.1)
        + min(10, td * 0.35)
        + 2 * is_portal,
        35, 96,
    )
if att < 80:
    w = sqrt(att / 80)             # w(0)=0, w(80)=1
    talent = (1-w) * recruiting_class_score + w * talent
```

Natural location for an established starter (att ≥ 80): about **67**,
not 50. 50 is the **missing-QB fill**, not league-average starter.

### 1.2 Source fields

| Field | Live 2026 source | Legal hist source |
|---|---|---|
| `pass_attempts_prior`, `pass_yards_prior`, `pass_td_prior` | ESPN athlete overview career split **labeled 2025** | ESPN core `seasons/{Y-1}/types/2/athletes/{id}/statistics` (`passingAttempts`, `passingYards` / `netPassingYards`, `passingTouchdowns`). CFBD player-season stats if a key is present. Warehouse PBP rollup if IDs join. |
| Starter identity | ESPN 2026 roster QBs, sort `(-att, -years, name)` | ESPN core **team athlete list for season Y**, same sort on Y−1 stats |
| `is_portal` | ESPN `teamHistory` has any other school | **Roster-year join:** on Y roster and (on a different Y−1 team, or Y−1 attempts at another school). Do not use live `teamHistory` without a year cutoff — later transfers leak. |
| `experience_abbr` / `experience_years` | ESPN roster experience (correct for 2026) | **Not** ESPN `athlete.experience` on a season-Y URL. That field is **current class** (McCord is SR/4 on the 2022, 2023, and 2024 athlete objects). Reconstruct: first season on an FBS roster or first season with attempts; `years ≈ Y - first_season`. |
| `recruiting_class_score` | Packaged 2026 prior (floor **55** when missing; 73/147 teams sit on 55) | Year-Y preseason recruiting only (CFBD `/recruiting/teams?year=Y` or a frozen composite). **MISSING** in-repo for 2022–25. Do not copy 2026 recruiting backward. |
| `ol_support` / `weapons_support` | Unit grades: `0.62*recruiting + 0.22*exp + 0.16*returning + 4*portal_share` | Same formula only after year-Y recruiting + year-Y roster exist. Otherwise **MISSING** (do not fill 50 and call it v1 cast). |
| Expert override | `cfb_qb_situation_overrides_2026.json` at read time | **MISSING** historically. Not part of the calibration contract. |
| W1 confirmed starter | `cfb_qb_confirmed_starters_w1_2026.json` (identity only; talent unchanged) | Legal for Week ≥ 2 of that season if `as_of` < kickoff. Reconstruct from Week 1 box **after** W1, never as W1’s own feature. |

### 1.3 Temporal cutoff

Production 2026 W1 **and** W2 still use the preseason snapshot. Talent
does not ingest 2026 game logs.

Canonical freeze:

- For every prediction in season Y, week 0–N (until an in-season talent
  updater is separately approved): counting stats are **season Y−1
  completed totals**.
- `stats_season == Y` is leakage under v1.
- `stats_season > Y` is leakage.
- End-of-season Y ratings, SOS, or recruiting revisions must not enter
  Week-N of Y (existing warehouse rule: strictly before kickoff).

Week-N **starter identity** may update from games 1…N−1 only (box
starter or a dated confirmation book). Week N’s own box is leakage for
Week N.

### 1.4 Starter-selection rules

1. Restrict to `position == QB` on the **season-Y** roster list.
2. Sort `(-prior_season_attempts, -experience_years, name)`.
3. QB1 = first row. Competing attempts = QB2 prior-season attempts.
4. Expert override / confirmation may replace **identity** only when the
   `starter_key` is already on that roster. They do not rewrite talent
   arithmetic.
5. No QB on roster → `qb_class=unknown`, `qb_talent=50`, fidelity
   `placeholder`. That is the only legal use of 50.

This heuristic will mis-name some camp battles. That is also what
production does. Calibration must repeat the heuristic, not the
after-the-fact true starter, except via a dated confirmation book.

### 1.5 Transfers / portal

Canonical (for train **and** a future serve audit):

```text
is_portal(Y) =
    player on team T’s season-Y roster
    AND (
      player on team U≠T’s season-(Y-1) roster
      OR player has Y-1 attempts while rostered elsewhere
    )
```

Live 2026 `teamHistory` “any prior school” is a close proxy for 2026
but is **not** year-safe for history. Hist builders must use the join.
A 2026 coverage table (teamHistory vs join) is an audit, not a ship.

True freshman vs portal freshman: first appearance + no Y−1 attempts +
not on another Y−1 FBS roster → `true_freshman`. First appearance with
Y−1 attempts at another school → `portal`.

### 1.6 Low-attempt blending

`att < 80`: blend toward **year-legal** `recruiting_class_score`.
If recruiting availability is MISSING or PROXY, **do not** inherit the
2026 floor of 55. Emit `availability=MISSING` and either:

- drop the row from the low-sample slice, or
- keep stats-only talent and exclude recruiting-dependent terms.

`att ≥ 80`: recruiting is unused. This is Layer A.

### 1.7 Missing semantics (must be explicit)

| Situation | Talent | Class | Availability |
|---|---|---|---|
| No QB on season-Y roster | 50 | unknown | MISSING |
| QB present, att=0, not portal | 48, then blend if recruiting legal | classify rules | EXACT or MISSING recruiting |
| QB present, att=0, portal | 52, then blend if recruiting legal | portal / open | same |
| Year-scoped stats 404 | treat as att=0 | classify with att=0 | MISSING stats |
| Recruiting absent, att<80 | stats-only or drop | classify | MISSING |
| Cast grades without recruiting | do not emit v1 cast | — | MISSING |
| ESPN experience used raw | illegal | illegal | — |

PROXY is a first-class failure. A builder that substitutes 2026
recruiting, current class year, or site-roster membership must raise,
not label EXACT.

### 1.8 Class semantics

Same serve rules (`classify_qb`):

| Class | Serve multiplier (unchanged; not re-fit now) |
|---|---|
| incumbent | 1.06 |
| portal | 0.95 |
| open_competition | 0.87 |
| true_freshman | 0.79 |
| unknown | 0.92 |

`experience_starts` proxy = `round(prior_attempts / 30)`.

### 1.9 Caps / floors

Talent clamp 35–96. Attempt term cap 22. YPA cap 12. TD cap 10.
Index soft ceiling knee 1.25 / τ 0.16 / rail 0.62–1.55. These are
**serve constants**. Do not retune them to chase 2026 closes.

### 1.10 Supporting-cast inputs

```text
supporting_cast = 0.55 * ol_support + 0.45 * weapons_support
cast_mult = 1 + 0.11 * (cast - 50) / 50
index_raw = (1 + (qb_talent-50)/80) * class_mult * cast_mult
```

`ol_support` / `weapons_support` are recruiting-anchored unit grades.
They are **Layer B**. Until year-Y recruiting is ingested, a v1 train
row may carry `ol_support`/`weapons_support` as MISSING and must not
pretend they are 50 “because hist-cal did.”

### 1.11 What is legal at prediction time (Week N, season Y)

Allowed:

- Season Y−1 completed player counting stats
- Season Y roster membership as of a stamp **before kickoff**
- Portal join from Y vs Y−1 rosters
- Reconstructed class from first-appearance
- Year-Y recruiting published before Week N (typically preseason)
- Confirmation / box starters from weeks `< N`
- Prior-year efficiency / SP+ (separate from this QB contract)
- Closing lines as **labels**, never as features

Forbidden:

- Season Y counting stats, EPA, or final SP+
- ESPN site roster `?season=Y` (returns the current 2026 club)
- Current `athlete.experience` applied to a past season
- 2026 recruiting / 2026 overrides copied onto 2023–24
- Week N box starter as a Week N feature
- 2025 game residuals (sealed)
- 2026 W1/W2 residuals as an objective

### 1.12 2026-only overlays (not in the fit contract)

Pipeline at serve: packaged ESPN qb → expert override → W1 confirm →
`build_qb_situation`.

Calibration uses the **packager heuristic** only. Overrides and
confirms are a 2026 sensitivity, reported separately, never in the loss.

---

## 2. Historical availability matrix

Classes: **EXACT** (same feed production uses) /
**RECONSTRUCTABLE** (different feed, same definition, no leakage) /
**PROXY** (forbidden unless a later note promotes it) /
**MISSING**.

Probed this run: ESPN core year-lock, year-scoped statistics, experience
leak, CFBD key absent, warehouse parquet **not** mounted on this VM
(documented on `/Volumes/KosEdgeData` + `data/ops/cfb-historical-warehouse-v1-20260812.md`).
SDV team box / betting / ratings CSVs exist locally for 2022–24 (team
grain, not player QB talent).

| Input | 2022 Y | 2023 Y | 2024 Y | 2025 Y | 2026 Y |
|---|---|---|---|---|---|
| Season-Y roster membership (ESPN core team athletes) | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | EXACT (packaged snapshot) |
| ESPN site roster (unscoped / `?season=`) | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN as hist source |
| Prior-year att/yds/td (ESPN year-scoped stats) | RECONSTRUCTABLE (2021 stats) | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | EXACT (2025 overview split) |
| Same-season att/yds/td as Week-0 talent | LEAKAGE | LEAKAGE | LEAKAGE | LEAKAGE | LEAKAGE (and unused live through W2) |
| Portal via Y vs Y−1 roster join | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE (audit vs live teamHistory) |
| Portal via live teamHistory, no year cut | PROXY | PROXY | PROXY | PROXY | EXACT-ish live method |
| Experience / class year (ESPN athlete.experience) | PROXY (current class) | PROXY | PROXY | PROXY | EXACT for 2026 serve |
| Experience via first-appearance / roster-year | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | RECONSTRUCTABLE | not needed |
| Recruiting class score (year-Y) | MISSING | MISSING | MISSING | MISSING | EXACT packaged (floor 55) |
| OL / weapons unit grades (recruiting-anchored) | MISSING | MISSING | MISSING | MISSING | EXACT live formula |
| Expert QB overrides | MISSING | MISSING | MISSING | MISSING | EXACT 2026 book |
| W1 confirmed starters | MISSING as a book; RECONSTRUCTABLE from W1 box for W2+ | same | same | SEALED | EXACT W1 book |
| Close spread/total + final scores | RECONSTRUCTABLE (warehouse / SDV; 2022 close n≈838) | EXACT-ish (close n≈907) | EXACT-ish (close n=965) | SEALED | confirmatory books only |
| Prior-year SP+ / adj-EPA efficiency | RECONSTRUCTABLE if year-specific file present; 2021 ratings not in this VM | 2022 ratings CSV present | 2023 ratings CSV present | SEALED | EXACT 2025 SP+ carry |
| Identity / option scheme tag | RECONSTRUCTABLE from prior-year rush/pass mix | same | same | SEALED | PROXY unless a frozen book exists |
| P4 / G5 | RECONSTRUCTABLE (affiliation map; realignments must be year-Y) | same | same | same | EXACT 2026 map |

**Usable historical universe under v1 Layer A** (talent + class + portal
+ starter heuristic, recruiting unused because att≥80 **or** recruiting
explicitly MISSING):

- **2022, 2023, 2024** Week-0 / early-week feature rows: reconstructable.
- **2025:** features would be legal (2024 stats + 2025 roster) but
  **labels stay sealed**. Do not build 2025 residual files in this pass.
- **2026:** already served. Confirmatory only.

**Not a v1 universe:** hist-cal `build_historical_proxy_state`
(`cfb-qb-feature-placeholder-unknown-50`). That is the 2026-08-05
training path that produced 1.40. It remains for forensics. It is
illegal for a new fit.

---

## 3. Leakage risks (do not hand-wave)

1. **End-of-season Y stats as Week-0 of Y.** The original failure mode
   named in the assignment. v1 forbids `stats_season == prediction_season`.
2. **ESPN site roster year leak.** `site.web.api` roster ignores
   `?season=` and returns the current club. Only core
   `seasons/{Y}/teams/{id}/athletes` is membership-safe.
3. **Experience drift.** Season-scoped athlete objects still return
   *today’s* class year. Using them makes 2023 true freshmen look like
   2026 juniors/seniors and destroys class multipliers.
4. **Stale `athlete.team` after departure.** McCord’s 2025/2026 athlete
   object still points at Syracuse. Membership SoT is the **team list**,
   not the athlete’s team `$ref`.
5. **Live teamHistory without a year cut.** A 2025 transfer looks like
   a 2023 portal starter.
6. **2026 recruiting / floor 55 copied backward.** Silent hierarchy
   leak and a false “year-Y” capital prior.
7. **Week N box starter as Week N feature.** After-the-fact identity.
8. **2025 residual peek.** Forbidden until an explicit unseal.
9. **2026 W1/W2 as the objective.** Restores Vegas-fitting. Confirmatory
   only.
10. **Placeholder@50 labeled v1.** The exact #539 failure. Contract
    tests reject it.
11. **In-season PBP talent while serve is frozen.** Hist would then be
    a different feature than 2026 W1/W2.
12. **Efficiency / SP+ year mismatch.** Separate from QB, but a v1 QB
    row sitting on the wrong year’s SP+ is still a leaked game.

---

## 4. Frozen train / validation / test design

Forward-chaining. Multiple seasons. 2025 sealed. 2026 not in the loss.

### Windows

| Split | Seasons / weeks | Features | Labels | Role |
|---|---|---|---|---|
| **Train-0** | 2022 W1–14 (FBS vs FBS; optional W15–bowl as sensitivity) | v1 Layer A at Week-0 freeze | actual scores + close | Fit candidates only after coverage gates |
| **Val-0** | 2023 W1–14 | same freeze, no 2023 in-season stats | actual + close | First out-of-time |
| **Train-1** | 2022+2023 W1–14 | refit on expanded train | — | Forward chain |
| **Val-1 (primary)** | **2024 W1–14** | v1 Layer A Week-0 freeze | actual + close | **Decision val** |
| **Sealed** | **2025 all** | do not score | do not score | Requires a written unseal |
| **Confirm** | **2026 W1/W2** joined books (n≈90) | live packaged v1 (already served) | actual + close | Report only. Never the objective. |

Optional walk-forward identity (not talent): after Week 1 of a train/val
season, QB1 may follow the prior week’s box if that rule is also applied
to a 2026 W2 sensitivity. Default is **Week-0 freeze for all weeks**,
matching live 2026 through W2.

Do not mix placeholder@50 rows into any split.

### What may change after a legal fit (not now)

Once train/serve share `cfb-qb-feature-v1`:

- `MATCHUP_RESPONSE` (and early soften) may be re-estimated
- `WEIGHT_QB_SITUATION` / `QB_INDEX_BLEND` / class multipliers may move
- They move because they would be calibrated on the **real** feature
  distribution (~67 center, not 50)

They do not move in this PR. 1.40 lives or dies on the 2024 val, not on
a 2026 residual chase.

---

## 5. Benchmark spec

Every split reports **vs actual** and **vs close**. n is required on
every cell. ATS / ROI are secondary and cannot pass a failed MAE/bias
gate.

### Primary

- Spread MAE / RMSE / bias vs actual margin and vs close
- Total MAE / RMSE / bias vs actual total and vs close
- Calibration by **projected-total bucket** (e.g. <48, 48–54, 54–60,
  60–68, ≥68). High-total tail = predicted total ≥ 68 (same as #539).

### Required slices (n on each)

- Favorite / underdog (model side and market side, labeled)
- Home favorite / home dog
- P4 vs P4, P4 vs G5, G5 vs G5 (year-Y affiliation)
- Identity / option vs everyone else — tag from **prior-year** rush
  rate / QB rush attempts (legal). If the tag cannot be built without
  same-season PBP, drop the slice; do not proxy from 2026 scheme.
- Early (W1–2) vs rest (because serve talent is a freeze)
- Established QB (att≥80) vs low-sample / MISSING recruiting

### Secondary

- ATS hit / unit ROI at −110, only on rows with close spread
- O/U hit / ROI at −110, only on rows with close total
- Brier on home WP

### Minimum evidence to **recalibrate** (all required)

1. Contract tests green (this PR’s suite plus coverage gates on the
   built dataset).
2. Layer A coverage: ≥ **90%** official FBS teams per train/val season
   with a named QB1, legal prior-year stats or documented att=0 fill,
   and portal flag from the year-join. Report the miss list.
3. Sample: train n (games with close+actual) ≥ **700**; primary val
   **2024** n ≥ **700**. Two-season forward chain actually run.
4. v1 talent location on each season’s QB1s: established mean ∈
   **[62, 76]**, sd ∈ **[5, 14]**. Reject mean∈[48,52] with sd<2.
5. Primary val (2024) graded on the frozen production *formula* with
   **new** v1 features (coefficients still 1.40) **and** at least one
   proposed coefficient set. Pick the set on 2024 val, not 2026.
6. 2026 W1/W2 confirmatory residual table published; a candidate is
   **not** discarded solely because 2026 mean total residual is still
   positive, and **not** accepted solely because it goes to ~0.
7. Layer B (recruiting / cast) either ingested as EXACT/RECONSTRUCTABLE
   or explicitly held out with a sensitivity that the chosen knobs are
   not identified off a 50-cast fill.
8. Written GO to unseal 2025 if anyone wants it as a second val.
   Default remains sealed.

If Layer A coverage < 90% or year-scoped stats 404 for a large G5
slice, **STOP and change architecture** (team-level prior-year QB
production index that does not require naming QB1). That is a later
call, triggered by coverage numbers, not by 2026 MAE.

---

## 6. Automated train/serve contract tests

Shipped in this PR (`tests/test_cfb_qb_feature_contract.py`):

| Check | What fails closed |
|---|---|
| Schema / version identity | Missing v1 fields; placeholder labeled as v1 |
| Packager ↔ spec formula | Live `package_real_roster_2026` drifts from the locked spec |
| Missing-value semantics | att=0 and no-QB fills |
| Low-sample + missing recruiting | 2026 floor 55 inherited silently |
| Temporal cutoff | same-season or future counting stats |
| Roster source | unscoped ESPN site roster |
| Experience source | raw ESPN `athlete.experience` for hist |
| Location | all-50 vector labeled v1; hist-cal proxy not @50 |
| Fit gate | `assert_legal_for_coefficient_fit(placeholder)` |
| Serve stamp | 2026 packaged universe + `project_game_to_dict` carry `cfb-qb-feature-v1` |
| Hist-cal stamp | proxy universe + grade payload carry placeholder |

Every model run now attaches `qb_feature_contract_version`:

- packaged 2026 universe / engine status / priors docs / game dict → **v1**
- hist-cal proxy / grade / priors snapshot → **placeholder**

`ENGINE_VERSION` is **not** bumped. Coefficients are unchanged.

When the dataset is built, add: per-season coverage %, forbidden-source
scan, and a CI job that refuses to run `run_historical_calibration.py`
as a coefficient fitter unless the universe stamp is v1.

---

## 7. Build plan (next assignment — not this PR)

Layer A (GO):

1. Pull ESPN core team athlete lists for 2021–2024 (membership).
2. For each season-Y QB, pull `seasons/{Y-1}` statistics.
3. Portal = Y vs Y−1 team-list join.
4. Class = first-appearance reconstruction (never raw experience).
5. Apply `qb_feature_contract` talent/class helpers.
6. Stamp every row `cfb-qb-feature-v1` + per-field availability.
7. Join warehouse/SDV games + closes. Do not open 2025 labels.
8. Run location + coverage gates. Stop if they fail.

Layer B (blocked): ingest year-specific recruiting 2022–25, then
rebuild unit grades / low-sample blend. Until then, cast stays MISSING.

Do not rematerialize KEI. Do not flip the public board. Do not fit λ.

---

## 8. GO / STOP (explicit)

**GO — build Layer A historical dataset** for 2022–2024 under
`cfb-qb-feature-v1`. The live QB talent definition can be reproduced
without feeding end-of-season statistics backward.

**STOP — do not recalibrate** MATCHUP_RESPONSE, QB weights, class
multipliers, or PPG. 1.40 is innocent until it is retried on v1
features. It is also not proven.

**STOP — do not ship** median→50, recruiting→50, or any diagnostic
location transform as “the fix.”

**STOP — keep CFB dark.** No PLAY. No public board. No Line Curve.

**STOP — different architecture** only if Layer A coverage fails.
That would mean we cannot name QB1 historically the way we name him
in production. We do not have that evidence yet. We have the opposite:
year-scoped rosters and year-scoped counting stats exist.

If Layer A is built and 2024 val says 1.40 is fine on the real
feature — keep it. If 2024 val says it is not — change it then.
Not because Grok guessed a coefficient. Because the contract matched.
