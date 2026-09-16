# KE Football v1 — Phase 2A unit ratings (Off/Def Efficiency)

**Date:** 2026-09-16
**Status:** `UNIT_RATINGS_PHASE2A` · `production_promote=false`
**Ryan (2026-09-16):** ACCEPT in scope as **PARTIAL v1 unit measurement only**. Do not advance phases.
**GO:** Ryan review of #570 Phase 1B → KE unit ratings research only. Team Strength **HOLD**.
**Continues:** [`KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md`](./KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md)
**Evidence:** `data/ops/ke-football-v1-phase2a-20260916/`
**Code:** `services/model-service/src/services/ke_football/unit_*.py`

Hierarchy: plays → measurements → **unit ratings** → (later) team strength → matchup → scoring → market.

This note constructs **KE Offensive Efficiency** (`ke.off_unit`) and **KE Defensive Efficiency** (`ke.def_unit`) only. It does **not** weight them into Team Strength.

---

## Hard stops honored

| Forbidden                                    | Status                                                 |
| -------------------------------------------- | ------------------------------------------------------ |
| Team Strength / overall Off+Def+ST weights   | `ke.team_strength` remains **OMIT**                    |
| Opponent-adjustment reopen                   | **Not reopened.** `NO_ADJUSTMENT_WINNER` accepted      |
| Scoring / matchup / market / ATS / ROI / CLV | Forbidden as construction and validation               |
| Production / UI / boards / public KE ratings | Untouched                                              |
| Named `ke.havoc` / CFB TFL-FF-INT / CFB ST   | Excluded (`DATA_INSUFFICIENT`)                         |
| Fake fills                                   | Missing PASS features fall back to shrunken EPA; no 50 |

Taxonomy unchanged: **RAW → DERIVED → ADJUSTED → MODELED**. Fitted ridge/PCA cells are MODELED. Shrunken/z composites of unadjusted measurements stay DERIVED. Week `W` uses only `week < W`. Selection-window fits are frozen before confirmation.

---

## Feature rules (Phase 1B lock)

PASS measurements are the initial set. PARTIAL may enter only if they improve selection MAE by ≥1% after z-standardization (incremental gate). DATA_INSUFFICIENT is excluded. NFL and CFB books are independent.

**Not unit quality:** pace, ST, RZ-TD sibling, named havoc, opp-adj.

**Finishing** (`ke.ppo`, `ke.finish`) stays available as PARTIAL after the NFL repair. It is **not** auto-promoted because the values are football-sane.

Live earned-PARTIAL lists are in the scorecard after the cached-PBP run.

---

## Methods compared

| Method         | What                                                                  | Layer   |
| -------------- | --------------------------------------------------------------------- | ------- |
| `epa_raw`      | Trailing play-weighted EPA (strongest constituent)                    | DERIVED |
| `epa_shrunken` | `μ + n/(n+k)×(EPA − μ)`; k chosen on the selection window             | DERIVED |
| `z_pass`       | Equal-weight z of PASS/CORE features, mapped to EPA units             | DERIVED |
| `z_earned`     | Same + PARTIAL features that cleared the incremental gate             | DERIVED |
| `pca_earned`   | First PC of earned z-features (loadings from selection, not outcomes) | MODELED |
| `ridge_earned` | Ridge of next-game EPA on earned z-features; λ from selection         | MODELED |

A composite is promoted only if it beats the strongest constituent (raw or shrunken EPA) on **frozen confirmation MAE** by ≥2%. **Complexity must earn inclusion.** If none do, the published unit rating is shrunken/raw EPA. That is an acceptable v1 result.

No arbitrary hand weights. No ATS objective.

---

## Validation

- Temporal OOS (selection vs confirmation)
- Early→late persistence
- Next-game unit EPA (not ATS)
- Incremental information after trailing EPA
- Week-to-week snapshot stability
- One-game outlier sensitivity
- Shrinkage weight / sample-strength `n/(n+k)` — **not** a confidence interval
- Ranking sanity (`n_games ≥ 4`)
- PIT leakage (future-week injection)

---

## Live result (2025 cached PBP)

**Call:** all four unit ratings are **`epa_shrunken` (k=160)** · grade **PARTIAL**. No z / PCA / ridge composite beat trailing EPA by 2% on frozen confirmation. Complexity did **not** earn inclusion.

That failure of the 2% composite hurdle does **not** by itself validate shrinkage. The trailing-EPA comparison is below. Opponent adjustment was not reopened. Future-week leakage: **False** on both sides, both sports.

Frozen numeric companion: `data/ops/ke-football-v1-phase2a-20260916/baseline_comparison.json` (derived from the existing Phase 2A JSON — no refit).

### NFL 2025 confirmation (weeks 11–18, n=214)

| Method                 |   Off MAE | Off r |   Def MAE | Def r | Beats EPA both sides? |
| ---------------------- | --------: | ----: | --------: | ----: | --------------------- |
| epa_raw                |     0.164 | 0.296 |     0.165 | 0.282 | baseline              |
| **epa_shrunken k=160** | **0.163** | 0.292 | **0.164** | 0.282 | winner (simple)       |
| z_pass                 |     0.164 | 0.298 |     0.167 | 0.258 | no                    |
| z_earned               |     0.164 | 0.298 |     0.170 | 0.230 | no                    |
| pca_earned             |     0.193 | 0.303 |     0.180 | 0.239 | no (worse)            |
| ridge_earned           |     0.163 | 0.313 |     0.170 | 0.159 | no                    |

Ridge offense is a MAE tie with slightly higher r (0.313). It does not clear the 2% cut. Do not promote it for the extra correlation.

PARTIAL incremental gate (selection only): NFL finishing **did not earn** (`ke.ppo` / `ke.finish` false). NFL defense `expl_allowed` + `disruption_proxy_nfl` earned on selection and **lost** confirmation — not published.

### CFB 2025 confirmation (weeks 9–13, n=446)

| Method                 |   Off MAE | Off r |   Def MAE | Def r | Beats EPA both sides? |
| ---------------------- | --------: | ----: | --------: | ----: | --------------------- |
| epa_raw                |     0.172 | 0.339 |     0.176 | 0.286 | baseline              |
| **epa_shrunken k=160** | **0.169** | 0.341 | **0.172** | 0.322 | winner (simple)       |
| z_pass                 |     0.173 | 0.319 |     0.176 | 0.286 | no                    |
| z_earned               |     0.173 | 0.319 |     0.175 | 0.292 | no                    |
| pca_earned             |     0.285 | 0.320 |     0.185 | 0.292 | no (worse)            |
| ridge_earned           |     0.173 | 0.318 |     0.173 | 0.293 | no                    |

CFB finishing came close on selection (PPO/finish MAE 0.170 vs z_pass 0.172) and **did not** clear the 1% earn cut. Not promoted because the values look football-sane.

### 1. Baseline: trailing EPA vs shrunken EPA

Unadjusted trailing EPA remains the baseline. `NO_ADJUSTMENT_WINNER` is held. Complex models missing the 2% confirmation hurdle does **not** validate `k=160`.

Δ = shrunken MAE − trailing MAE (negative = shrinkage better). Relative % = Δ / trailing MAE. Objective is next-game EPA/play MAE, not ATS.

**MAE SE / bootstrap is missing.** Pair-level residuals were not persisted. RMSE is shown only as scale. Do not read these deltas as a significance test.

#### Frozen confirmation (sealed)

| Unit    |   n | Trailing MAE | Shrunken MAE |    Abs Δ |      Rel % | Trailing RMSE | Shrunken RMSE |
| ------- | --: | -----------: | -----------: | -------: | ---------: | ------------: | ------------: |
| NFL off | 214 |      0.16435 |      0.16346 | −0.00090 | **−0.54%** |         0.209 |         0.207 |
| NFL def | 214 |      0.16499 |      0.16442 | −0.00057 | **−0.34%** |         0.208 |         0.207 |
| CFB off | 446 |      0.17226 |      0.16875 | −0.00351 | **−2.04%** |         0.219 |         0.212 |
| CFB def | 446 |      0.17626 |      0.17215 | −0.00411 | **−2.33%** |         0.220 |         0.213 |

NFL confirmation improvement is well under 2%. CFB confirmation is about 2%. Shrinkage is a **small, sealed-window point improvement**, not an independently proven estimator.

#### Selection window (where k was chosen)

| Unit    |   n | Trailing MAE | Shrunken MAE |    Abs Δ |  Rel % |
| ------- | --: | -----------: | -----------: | -------: | -----: |
| NFL off | 170 |      0.18131 |      0.17679 | −0.00451 | −2.49% |
| NFL def | 170 |      0.19682 |      0.18874 | −0.00808 | −4.11% |
| CFB off | 577 |      0.17694 |      0.17067 | −0.00627 | −3.54% |
| CFB def | 577 |      0.18808 |      0.17361 | −0.01447 | −7.70% |

Selection deltas are larger than confirmation. That is expected when k is picked on the same window it is scored on.

### 2. Shrinkage selection (`k=160`)

| Item                        | Fact                                                                          |
| --------------------------- | ----------------------------------------------------------------------------- |
| Season                      | **2025 only** (NFL REG as_of 18; CFB as_of 13). No other season.              |
| Folds                       | **None.** No k-fold, no nested holdout inside the selection window.           |
| Grid                        | `{0, 20, 40, 80, 160}` plays. `k=0` is trailing EPA. **160 is the grid cap.** |
| Objective                   | next-game EPA/play MAE (football only)                                        |
| NFL selection               | weeks **5–10**, n=170 team-games                                              |
| CFB selection               | weeks **4–8**, n=577 team-games                                               |
| Confirmation (sealed for k) | NFL weeks **11–18**; CFB weeks **9–13**                                       |
| Features at week W          | `week < W` only                                                               |

`k=160` is `argmin` of that selection-window MAE. The winning selection MAE is stored (`shrink_k_selection_mae`). The **full per-k MAE table was not persisted** — a documentation gap, not a hidden fold.

**Confirmation was not used to pick k.**

**Peek (say plainly):** after confirmation, `evaluate_methods` labeled the published winner `epa_shrunken` when confirmation MAE ≤ trailing MAE. That is a confirmation peek for the **binary publish label**, not for k. The table above is the comparison that label skipped past. On NFL confirmation the label prefers shrinkage despite a sub-1% MAE move.

No confirmation numbers were used to add grid points, change k, or re-open opponent adjustment.

### 3. Exact definition

Trailing EPA is **not** league-centered. It is the play-weighted mean of team-game EPA with `week < W`. League `μ` is the **unweighted mean of teams'** trailing EPA at that same `W` (PIT).

```text
w = n / (n + 160)                          # shrinkage weight / sample-strength
ke.off_unit = μ_off + w × (EPA_off_trailing − μ_off)
ke.def_unit = μ_def + w × (EPA_def_trailing − μ_def)

n     = trailing scrimmage plays on that side (off_epa_n / def_epa_n)
μ     = league mean of trailing team EPA at as_of W
layer = DERIVED
opp_adj_used = false
```

Equivalent: `w × EPA + (1 − w) × μ`.

**Defensive sign:** `ke.def_unit` is **EPA allowed per play**. **Lower is better defense.** The published number is not flipped. Do not read a higher `ke.def_unit` as a better defense.

### 4. Shrinkage weight — not uncertainty

`w = n/(n+160)` is a **shrinkage weight / sample-strength**.

- ~0.86 after a 16-game NFL season (~1000 plays)
- Lower early (more pull to `μ`)
- **Not** a calibrated variance
- **Not** a standard error
- **Not** a confidence interval
- **Not** a posterior width

MAE SE / bootstrap CI were not computed. Late snapshot week-to-week Pearson ≥ 0.97 is stability of the point rating, not a CI. Early→late persistence: NFL off 0.50 / def 0.39; CFB off 0.42 / def 0.26.

Incremental-on-EPA of the published unit is ~0 (it **is** shrunken EPA). That is expected, not a hidden signal.

### Ranking sanity (shrunken, n_games ≥ 4)

**NFL off:** NE 0.128, LA 0.121, GB 0.119, BUF 0.105, DAL 0.096, SF 0.093.
**NFL def:** HOU −0.114, SEA −0.090, CLE −0.079, JAX −0.078, MIN −0.074, PHI −0.069.
**CFB off:** Vanderbilt 0.258, NDSU 0.256, Ohio State 0.232, Navy 0.227, Indiana 0.226, USC 0.220.
**CFB def:** Texas Tech −0.175, Toledo −0.104, Oklahoma −0.096, Ohio State −0.091.

Same order as Phase 1B raw EPA, pulled toward league. One-game drop moves a mid NFL team ~0.03 EPA (CIN W3 vs MIN is the largest NFL off delta).

### Representative profiles (as_of 18 / 13)

| Team       | off unit | def unit | n_off plays | shrink weight `n/(n+k)` |
| ---------- | -------: | -------: | ----------: | ----------------------: |
| NE         |    0.128 |   −0.023 |         963 |                    0.86 |
| BUF        |    0.105 |   −0.002 |         995 |                    0.86 |
| SF         |    0.093 |    0.062 |        1023 |                    0.86 |
| PHI        |    0.031 |   −0.069 |         933 |                    0.85 |
| KC         |    0.059 |    0.012 |         986 |                    0.86 |
| HOU        |   −0.009 |   −0.114 |        1015 |                    0.86 |
| CLE        |   −0.165 |   −0.079 |         976 |                    0.86 |
| Ohio State |    0.232 |   −0.091 |         678 |                    0.81 |
| Georgia    |    0.137 |    0.047 |         779 |                    0.83 |

Full component z-contributions (for research composites that were **not** selected) stay in `nfl_phase2a.json` / `cfb_phase2a.json`.

### Scorecard

| Unit              | Grade       | Phase 2B Team Strength? | Recommendation                                       |
| ----------------- | ----------- | ----------------------- | ---------------------------------------------------- |
| NFL `ke.off_unit` | **PARTIAL** | HOLD                    | Honest v1 = shrunken EPA. Do not invent Off weights. |
| NFL `ke.def_unit` | **PARTIAL** | HOLD                    | Same. Disruption proxy did not survive confirmation. |
| CFB `ke.off_unit` | **PARTIAL** | HOLD                    | Same. Finishing not earned.                          |
| CFB `ke.def_unit` | **PARTIAL** | HOLD                    | Same. `success_allowed` earned on selection only.    |

**FAIL: 0.** Nothing was fit to the market.

#### What PARTIAL still leaves unvalidated

- Shrinkage vs trailing is a small confirmation point improvement (NFL ≪ 2%; CFB ~2%) with **no MAE SE / bootstrap**
- `k=160` is a **single-season grid-cap** choice, not a multi-season / nested-CV estimate
- Per-k selection table was not persisted
- Publish-label `epa_shrunken` used confirmation MAE vs trailing (peek on the label, not on k)
- No latent composite earned inclusion
- Defense is allowed-EPA (lower better) — not a flipped “higher = better D” rating

#### What PARTIAL permits

- Research / internal unit measurement on this branch
- Documentation, leakage tests, football sanity tables
- Holding `NO_ADJUSTMENT_WINNER`; unadjusted trailing remains the baseline

#### What PARTIAL forbids

- Team Strength input / Off+Def+ST overall weights
- Public KE ratings, UI, boards
- Scoring-model consume / matchup / market comparison
- ATS / ROI / CLV / close fitting
- Treating `n/(n+k)` as a CI
- Reopening opponent adjustment
- Advancing to Phase 2B

Eligible as the v1 **unit measurement continuation**. Not eligible as a new latent composite. Not Team Strength.

---

## How to reproduce

```bash
cd services/model-service
python3 -m pytest tests/test_ke_football_measurement.py tests/test_ke_football_phase1b.py tests/test_ke_football_phase2a.py -q

PYTHONPATH=services/model-service python3 scripts/ke_football/run_unit_ratings_phase2a.py
```

---

## STOP

Ryan lock after this amend. **No Phase 2B.**

Reviewable: trailing-vs-shrunken baseline, k-selection provenance, exact formula, shrinkage-weight label, PARTIAL permit/forbid.

**Not authorized:** Team Strength, Off/Def/ST overall weights, matchup, scoring projection, market comparison, ATS fitting, public UI, boards, production promote, opponent-adjustment reopen.
