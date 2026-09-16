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
