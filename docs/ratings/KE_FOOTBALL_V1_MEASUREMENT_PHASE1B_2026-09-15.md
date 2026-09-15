# KE Football v1 — Phase 1B measurement validation and repair

**Date:** 2026-09-15
**Status:** `MEASUREMENT_PHASE1B` · `production_promote=false`
**GO:** Ryan review of #570 Phase 1 → validation and repair only. Team Strength **HOLD**.
**Continues:** [`KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md`](./KE_FOOTBALL_V1_MEASUREMENT_PHASE1_2026-09-15.md)
**Evidence:** `data/ops/ke-football-v1-phase1b-20260915/`
**Code:** `services/model-service/src/services/ke_football/`

Phase 1 architecture is accepted provisionally. This note does **not** assign Team Strength weights, open boards, or compare to the market.

---

## Hard stops honored

| Forbidden                                    | Status                                                           |
| -------------------------------------------- | ---------------------------------------------------------------- |
| Team Strength / composite weights            | `ke.team_strength` remains **OMIT**                              |
| Scoring / matchup / market / ATS / ROI / CLV | Forbidden as construction and as validation                      |
| Production / UI / public KE ratings / boards | Untouched                                                        |
| Named `ke.havoc` / KE Disruption weights     | **OMIT**. CFB TFL/FF/INT stay `DATA_INSUFFICIENT`                |
| Calibrating around bad measurement           | NFL finishing repaired from owned PBP, not shrunk toward 2.1 PPO |
| #560 ridge promote / #562 retune             | Not used                                                         |

Taxonomy unchanged: **RAW → DERIVED → ADJUSTED → MODELED**. Week `W` consumes only `week < W`.

---

## 1. NFL finishing repair

Phase 1 PPO ~2.1 / finish ~0.41 was a **measurement defect**, not a football truth. Kickoffs sit at `yardline_100 ≈ 35` and share `fixed_drive` with the receiving offense, so almost every drive looked like a scoring opportunity.

Repair (owned nflverse only):

- Drive key = `(game_id, fixed_drive)`
- Drive offense = scrimmage `posteam` (kickoff ST-swap does not steal the drive)
- Opportunity yardline **ignores** kickoff / extra-point / kickoff-return snaps
- Kickoff-only / XP-only rows are not offensive drives
- Points from `fixed_drive_result` + same-drive XP/2pt flags
- No synthetic PAT. **Not calibrated** toward a target PPO

CFB finishing keeps the #555 `type.text` heuristic (already football-sane). CFB TFL/FF/INT remain `DATA_INSUFFICIENT`. No fake havoc rates.

Live numbers after the cached-PBP run are in `data/ops/ke-football-v1-phase1b-20260915/finishing_diagnosis.json` and the scorecard.

---

## 2. Per-component validation

NFL and CFB are scored separately. Each available component is evaluated for:

- sample-size split-half curves (first n vs next n games)
- week-to-week reliability
- early-season → later-season persistence
- OOS prediction of **future football** (own unit, EPA, success, expl, finishing) — **not ATS**
- distribution / range / outliers
- season/week missingness
- offense/defense symmetry (league off mean ≈ def mean)
- correlation matrix among KE components
- incremental signal conditional on trailing EPA (reported, not used to drop a distinct construct)

See `nfl_component_validation.json` / `cfb_component_validation.json`.

---

## 3. Opponent-adjustment bakeoff

Phase 1 simple SOS failed to improve next-game EPA. That result is preserved as `loo_sos`.

Candidates (all PIT, week `< W`; SOS-style methods are leave-one-game-out):

| Method                   | Notes                                  |
| ------------------------ | -------------------------------------- |
| `unadjusted`             | trailing play-weighted EPA             |
| `loo_sos`                | Phase 1 PIT SOS (preserved)            |
| `shrunken_sos_k{4,8,16}` | SOS × n/(n+k)                          |
| `iterative_twoway`       | two-way offense/defense, centered      |
| `iterative_ridge_l40`    | same family as #560, **not** a promote |
| `schedule_network`       | one-step opponent-of-opponent SOS      |

Selection weeks are not the confirmation seal. A method must beat unadjusted on **both** offense and defense MAE by ≥2% in the frozen confirmation window. **`NO_ADJUSTMENT_WINNER` is acceptable.**

No ATS / close / ROI / CLV / market residual.

---

## 4. Football sanity

`sanity.json`: top/bottom tables per measurement (`n_games ≥ 4`), representative team-week breakdowns, and rank conflicts vs play-level off EPA. Conflicts are flagged for inspection — not auto-corrected, not a board.

---

## 5. Scorecard

`SCORECARD.md` + `scorecard.json`: **PASS / PARTIAL / FAIL / DATA_INSUFFICIENT** per component, with evidence and Phase 2 eligibility.

Phase 2 (not this GO) may consume PASS/PARTIAL measurements only. This PR assigns **no weights**.

---

## How to reproduce

```bash
cd services/model-service
python3 -m pytest tests/test_ke_football_measurement.py tests/test_ke_football_phase1b.py -q

PYTHONPATH=services/model-service python3 scripts/ke_football/run_measurement_phase1b.py
```

PBP cache remains gitignored at `data/cfb/research/ke_football_pbp/`. Do not write 2026 into the Aug 13 historical lake.

---

## STOP

Reviewable now: finishing repair, per-component validation, PIT bakeoff, sanity tables, scorecard.

**Not authorized:** Team Strength composite, scoring integration, matchup modeling, market comparison, public KE ratings, UI, boards, named KE Disruption weighting, production promote.
