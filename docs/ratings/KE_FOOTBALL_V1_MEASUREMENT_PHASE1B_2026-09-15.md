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

| Forbidden                                    | Status                                                               |
| -------------------------------------------- | -------------------------------------------------------------------- |
| Team Strength / composite weights            | `ke.team_strength` remains **OMIT**                                  |
| Scoring / matchup / market / ATS / ROI / CLV | Forbidden as construction and as validation                          |
| Production / UI / public KE ratings / boards | Untouched                                                            |
| Named `ke.havoc` / KE Disruption weights     | **OMIT**. CFB TFL/FF/INT stay `DATA_INSUFFICIENT`                    |
| Calibrating around bad measurement           | NFL finishing repaired from owned PBP; **not** shrunk toward 2.1 PPO |
| #560 ridge promote / #562 retune             | Not used as a coefficient source                                     |

Taxonomy unchanged: **RAW → DERIVED → ADJUSTED → MODELED**. Week `W` consumes only `week < W`. Live leakage probe: future-week injection does **not** change any snapshot or bakeoff method (NFL and CFB).

---

## 1. NFL finishing repair (do not calibrate around the defect)

Phase 1 PPO ~2.1 / finish ~0.41 was a **measurement defect**. Kickoffs sit at `yardline_100 ≈ 35` and share `fixed_drive` with the receiving offense.

| Check (NFL 2025 REG, week &lt; 18) |                                          Value |
| ---------------------------------- | ---------------------------------------------: |
| Kickoffs                           |                                          2,645 |
| Kickoffs with yl ≤ 40              |                              2,629 (**99.4%**) |
| Offensive drives after repair      |                                          5,200 |
| Scoring-opportunity rate           |                                      **0.521** |
| PPO (repaired)                     |                                       **3.95** |
| Finish rate (repaired)             |                                      **0.748** |
| Calibrated toward a target?        |                                         **No** |
| Points source                      | `fixed_drive_result` + same-drive XP/2pt flags |

Repair (owned nflverse only):

- Drive key = `(game_id, fixed_drive)`
- Drive offense = scrimmage `posteam` (kickoff ST-swap does not steal the drive)
- Opportunity yardline **ignores** kickoff / extra-point / kickoff-return snaps
- Kickoff-only / XP-only rows are not offensive drives
- No synthetic PAT

Some team-games still fall back to `offensive_scoring_flags_fallback` when `fixed_drive_result` is missing on that drive. That is labeled, not filled. CFB finishing keeps the #555 `type.text` heuristic (already football-sane; Georgia PPO 4.28 / Ohio State 4.72).

**Do not** treat the old 2.1 / 0.41 band as a prior.

---

## 2. Per-component validation (NFL and CFB separate)

Each available component was scored for sample-size split-half curves, week-to-week reliability, early→late persistence, OOS **football** prediction (own unit / EPA / success / expl / finish — **not ATS**), distribution, missingness, O/D symmetry, correlation matrix, and incremental signal after trailing EPA.

Single-game week-to-week EPA is noisy by construction (~0.08 late NFL). That is reported; it is not a PASS veto when split-half and early→late already hold. Trailing-snapshot stability from Phase 1 (0.92+ by midseason) remains the right reliability view for composites later.

### NFL 2025 (512 team-games, 32 teams)

| ID                                                    | Grade                 | Phase 2 | Why                                                                                     |
| ----------------------------------------------------- | --------------------- | ------- | --------------------------------------------------------------------------------------- |
| `ke.off_eff`                                          | **PASS**              | yes     | Early→late r=0.50; split-half n=4 r=0.54; next-game EPA r=0.27 n=448                    |
| `ke.def_eff`                                          | PARTIAL               | yes     | Persists (0.39) but next-game r=0.19 — usable, thinner than offense                     |
| `ke.success_native` / `standard` / `allowed`          | **PASS**              | yes     | Success tracks EPA (r≈0.91 with off EPA) and predicts next-game                         |
| `ke.off_pass_epa`                                     | **PASS**              | yes     | Split-half n=4 r=0.65; next-game EPA r=0.26. Split, not a second rating                 |
| `ke.off_rush_epa` / `ke.off_early_epa`                | PARTIAL               | yes     | Rush split is weaker; keep labeled                                                      |
| `ke.pace` (+ competitive / seconds)                   | PARTIAL               | yes     | ~60.6 plays/game. Own-unit OOS is weak. Publish, do not convert to points               |
| `ke.expl` / `expl_pass` / `expl_allowed`              | PARTIAL               | yes     | Combined expl ~9.6%. Pass split more stable than rush                                   |
| `ke.expl_rush`                                        | PARTIAL               | yes     | **Weak:** early→late 0.04; OOS ≈0. Do not overweight                                    |
| `ke.ppo`                                              | PARTIAL               | yes     | Mean **3.92** after repair (was ~2.1). Next-game finish/PPO is noisy                    |
| `ke.finish`                                           | PARTIAL               | yes     | Mean **0.74**. Football-sane now; next-game own-unit r=0.03 — measurement, not a weight |
| `ke.opp_rate`                                         | **PASS**              | yes     | Mean 0.53; next-game EPA r=0.26; some incremental-on-EPA (r=0.06)                       |
| `ke.rz_td`                                            | PARTIAL               | yes     | Sibling only. Must not be named `ke.finish`                                             |
| `ke.st`                                               | PARTIAL               | yes     | NFL ST EPA/play published; no 1.0 hook; uncertified as a rating                         |
| `ke.havoc`                                            | **DATA_INSUFFICIENT** | no      | Raw TFL∧FF∧INT inventory-ok, still **OMIT** until a certify/weight GO                   |
| NFL disruption events (sack/INT/qb_hit/fumble/FF/TFL) | PARTIAL               | yes     | Per-event rates only. Null-rate 0 on raw nflverse                                       |
| `ke.disruption_pass_breakup`                          | **DATA_INSUFFICIENT** | no      | Absent                                                                                  |
| `ke.disruption_proxy_nfl`                             | PARTIAL               | yes     | sack∨INT∨qb_hit. Must not be named havoc                                                |
| `ke.opp_adj_epa`                                      | PARTIAL               | **no**  | `NO_ADJUSTMENT_WINNER`                                                                  |

League off EPA mean = def EPA mean (identity gap 0). Team off vs def r≈−0.06.

### CFB 2025 (1,624 team-games, as_of 13)

| ID                                     | Grade                       | Phase 2 | Why                                                                   |
| -------------------------------------- | --------------------------- | ------- | --------------------------------------------------------------------- |
| `ke.off_eff`                           | **PASS**                    | yes     | Early→late r=0.42; next-game r=0.30 n=1,149                           |
| `ke.def_eff`                           | PARTIAL                     | yes     | Next-game r=0.23; team-level off/def r=−0.37 (FBS quality clustering) |
| `ke.success_native` / `standard`       | **PASS**                    | yes     | Both stay. Do not swap native vs 50/70/100                            |
| `ke.expl` / `expl_pass`                | **PASS**                    | yes     | CFB knobs (EPA≥1 or 15 yd). Combined expl mean ~0.20                  |
| `ke.expl_rush` / `expl_allowed`        | PARTIAL                     | yes     | Publish splits                                                        |
| `ke.ppo` / `ke.finish` / `ke.opp_rate` | PARTIAL / PASS (`opp_rate`) | yes     | Ohio State PPO 4.72 / finish 0.88; Wisconsin 1.68 / 0.33              |
| `ke.st`                                | **DATA_INSUFFICIENT**       | no      | Uncertified — OMIT. Do not manufacture                                |
| `ke.havoc`                             | **DATA_INSUFFICIENT**       | no      | OMIT                                                                  |
| sack                                   | PARTIAL                     | yes     | Only CFB disruption rate that clears the 5% null bar                  |
| TFL / FF / INT / PBU / qb_hit / fumble | **DATA_INSUFFICIENT**       | no      | Sparse / event-only / absent. **No fake rates**                       |
| `ke.opp_adj_epa`                       | PARTIAL                     | **no**  | `NO_ADJUSTMENT_WINNER`                                                |

**FAIL count: 0.** Nothing was calibrated around a known bad number.

Incremental-on-EPA is near 0 for most efficiency cousins (they are collinear with EPA). That is reported, not a reason to drop success or PPO as distinct **measurements**. It is a reason not to double-count them in a later composite.

---

## 3. Opponent-adjustment bakeoff — `NO_ADJUSTMENT_WINNER`

Phase 1 simple SOS failed to beat trailing unadjusted. Preserved.

All candidates are PIT (`week < W`). SOS-style methods are leave-one-game-out. Confirmation weeks are **not** the selection window. A promote required **both** sides to beat unadjusted MAE by ≥2%. None did. Closest NFL method (`iterative_ridge_l40`) is 0.1635 vs 0.1644 off — inside noise, and defense does not clear the cut.

### NFL confirmation (weeks 11–18)

| Method                |    Off MAE |       Def MAE | Beats unadj both sides? |
| --------------------- | ---------: | ------------: | ----------------------- |
| **unadjusted**        | **0.1644** |    **0.1650** | baseline                |
| loo_sos (Phase 1)     |     0.1648 |        0.1660 | no                      |
| shrunken_sos k=4/8/16 |     0.1647 | 0.1659–0.1660 | no                      |
| iterative_twoway      |     0.1642 |        0.1656 | no                      |
| iterative_ridge_l40   |     0.1635 |        0.1651 | no                      |
| schedule_network      |     0.1651 |        0.1661 | no                      |

### CFB confirmation (weeks 9–13)

| Method              |       Off MAE |       Def MAE | Beats unadj both sides? |
| ------------------- | ------------: | ------------: | ----------------------- |
| **unadjusted**      |    **0.1723** |    **0.1763** | baseline                |
| loo_sos             |        0.1791 |        0.1792 | no (worse)              |
| shrunken_sos        | 0.1779–0.1787 | 0.1784–0.1790 | no                      |
| iterative_twoway    |        0.1843 |        0.2110 | no (worse)              |
| iterative_ridge_l40 |        0.1779 |        0.1956 | no                      |
| schedule_network    |        0.1809 |        0.1813 | no                      |

**Call:** `NO_ADJUSTMENT_WINNER` on both sports. Do not promote an opponent adjustment because it is theoretically desirable. Phase 2 may keep the PIT SOS cell as **ADJUSTED-not-promoted** research. #560 ridge stays MODELED research and is not imported as a weight.

No ATS / close / ROI / CLV / market residual was used.

---

## 4. Football sanity

`n_games ≥ 4`. Not a board.

**NFL offense EPA:** NE 0.148, LA 0.139, GB 0.138, BUF 0.120, DAL 0.109, SF 0.106.
**NFL defense EPA allowed:** HOU −0.136, SEA −0.106, CLE −0.095, JAX −0.092, MIN −0.088, PHI −0.082.
**NFL worst offense:** LV −0.196, CLE −0.194, TEN −0.149.

Repaired finishing no longer looks broken: IND PPO 4.75 / finish 0.89; BUF 4.43; NO 2.96 / 0.61. That matches play-level EPA much better than the Phase 1 2.1 band.

Flagged rank conflicts vs off EPA (inspect, do not auto-correct): HOU finish rank 3 vs EPA rank 24 (good finishing, pedestrian offense EPA); LA finish 21 vs EPA 3 (efficient EPA, average finish); BAL expl 1 vs EPA 14.

**CFB offense EPA:** Vanderbilt 0.326, NDSU 0.321, Ohio State 0.292, Navy 0.286, Georgia Tech 0.276, USC 0.274.
**CFB defense:** Texas Tech −0.238, Toledo −0.163, Ohio State −0.153, Oklahoma −0.151.
**CFB finishing:** Ohio State 4.72 / 0.88; Indiana 4.66 / 0.86; Wisconsin 1.68 / 0.33.

Representative team-weeks (first / mid / last) are in `sanity.json`. Example: BUF W1 vs BAL off EPA 0.235 / PPO 5.12 / finish 1.00; W17 vs PHI −0.121 / 2.40 / 0.40.

---

## 5. What may enter Phase 2

Eligible as **independent measurements** only. This PR assigns **no weights**.

**Take:** NFL `off_eff`, success trio, `off_pass_epa`, `opp_rate`. CFB `off_eff`, success (both), `expl` / `expl_pass`, `opp_rate`.

**Take with caveats:** NFL/CFB finishing (now football-sane; noisy next-game), expl (rush split weak in NFL), pace, ST (NFL only), NFL per-event disruption, CFB sack.

**Do not take:** named `ke.havoc`, CFB TFL/FF/INT/PBU, CFB ST, opponent-adjustment as a promoted layer, Team Strength, any market-fit weight.

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

Reviewable now: finishing repair, per-component validation, PIT bakeoff (`NO_ADJUSTMENT_WINNER`), sanity tables, scorecard.

**Not authorized:** Team Strength composite, scoring integration, matchup modeling, market comparison, public KE ratings, UI, boards, named KE Disruption weighting, production promote.
