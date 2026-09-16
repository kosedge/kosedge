# KE Football v1 — Phase 2A unit ratings (Off/Def Efficiency)

**Date:** 2026-09-16
**Status:** `UNIT_RATINGS_PHASE2A` · `production_promote=false`
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
| `epa_shrunken` | EPA × n/(n+k) toward league; k chosen on selection                    | DERIVED |
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
- Uncertainty / sample-strength `n/(n+k)`
- Ranking sanity (`n_games ≥ 4`)
- PIT leakage (future-week injection)

---

## Live result (2025 cached PBP)

**Call:** all four unit ratings are **`epa_shrunken` (k=160)** · grade **PARTIAL**. No z / PCA / ridge composite beat trailing EPA by 2% on frozen confirmation. Complexity did **not** earn inclusion. That is the honest v1 unit rating.

Opponent adjustment was not reopened. Future-week leakage: **False** on both sides, both sports.

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

### What the published unit rating is

```text
ke.off_unit = shrink(trailing off EPA, n_plays, k=160, league)
ke.def_unit = shrink(trailing def EPA, n_plays, k=160, league)
layer = DERIVED
opp_adj_used = false
```

Sample-strength `n/(n+160)` is the uncertainty indicator (~0.86 after a 16-game NFL season; lower early). Late snapshot week-to-week Pearson ≥ 0.97. Early→late persistence: NFL off 0.50 / def 0.39; CFB off 0.42 / def 0.26.

Incremental-on-EPA of the published unit is ~0 (it **is** shrunken EPA). That is expected, not a hidden signal.

### Ranking sanity (shrunken, n_games ≥ 4)

**NFL off:** NE 0.128, LA 0.121, GB 0.119, BUF 0.105, DAL 0.096, SF 0.093.
**NFL def:** HOU −0.114, SEA −0.090, CLE −0.079, JAX −0.078, MIN −0.074, PHI −0.069.
**CFB off:** Vanderbilt 0.258, NDSU 0.256, Ohio State 0.232, Navy 0.227, Indiana 0.226, USC 0.220.
**CFB def:** Texas Tech −0.175, Toledo −0.104, Oklahoma −0.096, Ohio State −0.091.

Same order as Phase 1B raw EPA, pulled toward league. One-game drop moves a mid NFL team ~0.03 EPA (CIN W3 vs MIN is the largest NFL off delta).

### Representative profiles (as_of 18 / 13)

| Team       | off unit | def unit | n_off plays | sample strength |
| ---------- | -------: | -------: | ----------: | --------------: |
| NE         |    0.128 |   −0.023 |         963 |            0.86 |
| BUF        |    0.105 |   −0.002 |         995 |            0.86 |
| SF         |    0.093 |    0.062 |        1023 |            0.86 |
| PHI        |    0.031 |   −0.069 |         933 |            0.85 |
| KC         |    0.059 |    0.012 |         986 |            0.86 |
| HOU        |   −0.009 |   −0.114 |        1015 |            0.86 |
| CLE        |   −0.165 |   −0.079 |         976 |            0.86 |
| Ohio State |    0.232 |   −0.091 |         678 |            0.81 |
| Georgia    |    0.137 |    0.047 |         779 |            0.83 |

Full component z-contributions (for research composites that were **not** selected) stay in `nfl_phase2a.json` / `cfb_phase2a.json`.

### Scorecard

| Unit              | Grade       | Phase 2B Team Strength? | Recommendation                                       |
| ----------------- | ----------- | ----------------------- | ---------------------------------------------------- |
| NFL `ke.off_unit` | **PARTIAL** | HOLD                    | Honest v1 = shrunken EPA. Do not invent Off weights. |
| NFL `ke.def_unit` | **PARTIAL** | HOLD                    | Same. Disruption proxy did not survive confirmation. |
| CFB `ke.off_unit` | **PARTIAL** | HOLD                    | Same. Finishing not earned.                          |
| CFB `ke.def_unit` | **PARTIAL** | HOLD                    | Same. `success_allowed` earned on selection only.    |

**FAIL: 0.** Nothing was fit to the market.

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

Reviewable: unit-rating candidates, contributions, uncertainty, OOS vs EPA, scorecard.

**Not authorized:** Team Strength, Off/Def/ST overall weights, matchup, scoring projection, market comparison, ATS fitting, public UI, boards, production promote.
