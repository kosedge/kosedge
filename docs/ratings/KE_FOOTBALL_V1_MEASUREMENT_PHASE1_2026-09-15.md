# KE Football v1 — Phase 1 measurement (research)

**Date:** 2026-09-15  
**Status:** `MEASUREMENT_PHASE1` · `production_promote=false`  
**GO:** Ryan review of #569 → implement measurement only.  
**Taxonomy:** [`KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md`](./KE_FOOTBALL_V1_PROVENANCE_AMEND_2026-09-15.md) — **RAW → DERIVED → ADJUSTED → MODELED**  
**Evidence:** `data/ops/ke-football-v1-measurement-20260915/`  
**Code:** `services/model-service/src/services/ke_football/`

This is a research artifact so measurements can be football-sanity inspected. It is **not** a ratings book, not KEI, not a spread, not Team Strength.

---

## Hard stops honored

| Forbidden                                                 | Status                                          |
| --------------------------------------------------------- | ----------------------------------------------- |
| KE Overall / Team Strength weighting                      | `ke.team_strength` = **OMIT** on every snapshot |
| Scoring-model integration                                 | No `a`/`b`/pace conversion. #562 not used       |
| Matchup interaction                                       | Not implemented                                 |
| Market integration / ATS / ROI                            | Forbidden as construction and as validation     |
| Production promotion / UI / public ratings / board reopen | Flags untouched                                 |
| Named `ke.havoc` composite                                | **OMIT**. Inventory only. **No weights**        |
| #560 ridge re-fit                                         | Not run. Stays MODELED research candidate       |
| PFF / CFBD / silent fills                                 | None                                            |

NFL is the reference implementation. CFB shares names and infrastructure; knobs stay sport-specific.

---

## What was built

Team-week snapshots as-of week `W` using only `week < W`. Every component carries native units + layer + status + `n`. Missing required inputs → `DATA_INSUFFICIENT` or documented `PARTIAL`. No 50, no `1.0` ST hook, no league-mean EPA fill.

| ID                                     | Layer        | NFL 2025 W&lt;18                     | CFB 2025 W&lt;13                                         |
| -------------------------------------- | ------------ | ------------------------------------ | -------------------------------------------------------- |
| `ke.off_eff` / `ke.def_eff`            | DERIVED      | **OK** 32/32                         | OK 183 / THIN 49 (off)                                   |
| Success native + standard              | DERIVED      | both published                       | both published (do not swap)                             |
| Pass / rush / early EPA                | DERIVED      | splits published                     | splits published                                         |
| `ke.pace` (+ competitive)              | DERIVED      | plays/game                           | plays/game (~66–71 for Power schools)                    |
| `ke.expl` + pass/rush                  | DERIVED      | NFL 20/10 **complete**               | CFB EPA≥1 or 15 yd                                       |
| `ke.ppo` / `ke.finish` / `ke.opp_rate` | DERIVED      | published (see finishing note)       | published; Georgia PPO 4.29 / finish 0.81                |
| `ke.st`                                | DERIVED      | NFL ST EPA/play (unvalidated module) | **OMIT**                                                 |
| `ke.havoc`                             | —            | **OMIT**                             | **OMIT**                                                 |
| Disruption events                      | DERIVED      | per-event rates; NFL proxy labeled   | sack OK; TFL/FF/INT **DATA_INSUFFICIENT** (sparse flags) |
| `ke.opp_adj_epa`                       | **ADJUSTED** | PIT leave-one-out SOS                | same                                                     |
| #560 ridge                             | MODELED      | not emitted                          | not emitted                                              |
| `ke.team_strength`                     | —            | **OMIT**                             | **OMIT**                                                 |

---

## Provenance amend (do-first)

#569 specified three layers. Phase 1 amends:

```text
RAW → DERIVED → ADJUSTED → MODELED
```

Opponent adjustment is **ADJUSTED** unless a genuinely fitted model is involved. Phase 1 SOS:

```text
off_adj(g) = off_raw(g) − (opp_def_other(week < W) − league_def(week < W))
```

Same-game opponent observations are excluded. Week 1-only windows are `DATA_INSUFFICIENT` for ADJUSTED (no other opponent book — not a 0 fill). #560 joint-ridge remains MODELED, `production_promote=false`, not a coefficient source.

---

## Data truth (owned only)

| Sport | Source                                   | Window   | Plays in window | Team-games | Snapshots |
| ----- | ---------------------------------------- | -------- | --------------- | ---------- | --------- |
| NFL   | nflverse `play_by_play_2025.parquet` REG | as_of 18 | 39,032          | 512        | 32        |
| CFB   | SDV `espn_cfb_pbp` 2025                  | as_of 13 | 140,911         | 1,624      | 232       |

CFB file was written to gitignored `data/cfb/research/ke_football_pbp/` — **not** the Aug 13 historical lake. Railway still has **no** worker parquet volume. That remains a platform gap, not a vendor purchase. This PR does not add a production copy or promote ratings.

#559/#560: definitions and eligibility lessons are reused (scrimmage filter, `EPA_success` vs 50/70/100, OT out of ADJUSTED, delayed-game fail-closed). Their tables are not production-promoted. #562 is not used.

---

## KE Disruption inventory (no weights)

`weight = null` on every event. Named `ke.havoc` requires certified TFL ∧ FF ∧ INT. That GO is not this PR.

| Event           | NFL raw 2025                        | CFB raw 2025                         | Phase 1 publish                 |
| --------------- | ----------------------------------- | ------------------------------------ | ------------------------------- |
| sack            | present, null 0, n_true 1,207       | present, null 0, n_true 3,161        | rate OK both                    |
| interception    | present, null 0                     | present, **null 0.989** (event-only) | NFL OK; CFB `DATA_INSUFFICIENT` |
| qb_hit          | present, null 0                     | absent                               | NFL OK; CFB omit                |
| fumble          | present, null 0                     | absent                               | NFL OK; CFB omit                |
| fumble_forced   | present on **raw** nflverse, null 0 | present, **null 0.997**              | NFL OK; CFB `DATA_INSUFFICIENT` |
| tackle_for_loss | present on **raw** nflverse, null 0 | present, **null 0.914**              | NFL OK; CFB `DATA_INSUFFICIENT` |
| pass_breakup    | absent                              | present, null 0.979                  | both insufficient / absent      |

Honesty vs #569 matrix: the **normalized mart** still lacks TFL/FF. **Raw nflverse** in this run has both with null-rate 0. That is inventory, not a certify-and-weight GO. Named `ke.havoc` stays OMIT. The NFL proxy (`sack ∨ INT ∨ qb_hit`) is published under `ke.disruption_proxy_nfl` only.

CFB TFL/FF/INT are event-only flags (almost only `true` rows exist). Publishing `1.00` on the non-null subset is forbidden; those cells are `DATA_INSUFFICIENT`.

---

## Leakage tests

Unit tests (`tests/test_ke_football_measurement.py`, 18 passed):

1. `week < W` is strict.
2. Week-1 ADJUSTED is `DATA_INSUFFICIENT`.
3. Injected week=`W` game with EPA=99 does **not** change the as-of-`W` ADJUSTED book.
4. Same-game opponent observations are left out.
5. Team Strength / named havoc / CFB ST omitted.
6. Sparse disruption flags do not become 1.0.

Live PBP probe (same injection on the real 2025 slates):

|                   | future week changes snapshot? |
| ----------------- | ----------------------------- |
| NFL 2025 as_of 18 | **False**                     |
| CFB 2025 as_of 13 | **False**                     |

---

## Validation (football only)

Construction / first gate is **next-game EPA/play**, not ATS.

### NFL 2025 (n=448 next-game obs, as_of ≥ 3)

| Predictor           |   Off MAE |   Def MAE |
| ------------------- | --------: | --------: |
| ADJUSTED PIT SOS    |     0.177 |     0.181 |
| Unadjusted trailing | **0.173** |     0.178 |
| League mean         |     0.175 | **0.175** |

ADJUSTED does **not** beat unadjusted or league on this window. That is expected for a no-shrink, no-prior SOS, and is **not** a reason to import #560 λ or #562 coefficients. Report only.

Week-to-week `ke.off_eff` Pearson: 0.68 (W2→3) → 0.92 (W4→5) → 0.99 late. Stabilizes with sample. No 50-fill.

### CFB 2025 (n≈1,147–1,172)

| Predictor           |   Off MAE |   Def MAE |
| ------------------- | --------: | --------: |
| ADJUSTED PIT SOS    |     0.196 |     0.193 |
| Unadjusted trailing | **0.182** |     0.189 |
| League mean         |     0.185 | **0.185** |

Same shape. #560 fitted ridge (holdout MAE 0.167) is a **MODELED** candidate and was not re-run or promoted.

Stability: 0.90 by W2→3, 0.98+ from W4. THIN cells stay THIN (49 offense snapshots under 80 plays).

### Ranking sanity (n_games ≥ 4)

**NFL offense (EPA/play):** NE 0.148, LA 0.139, GB 0.138, BUF 0.120, DAL 0.109, SF 0.106.  
**NFL defense (EPA allowed):** HOU −0.136, SEA −0.106, CLE −0.095, JAX −0.092, MIN −0.088, PHI −0.082.  
**NFL worst offense:** LV −0.196, CLE −0.194, TEN −0.149.

**CFB offense:** Vanderbilt 0.326, NDSU 0.321, Ohio State 0.292, Navy 0.286, Georgia Tech 0.276, USC 0.274.  
**CFB defense:** Texas Tech −0.238, Toledo −0.163, Ohio State −0.153, Oklahoma −0.151, SDSU −0.135, Indiana −0.133.

One-game FCS spikes were excluded from the sanity board (`min_games=4`). They remain in the snapshot file as THIN / small-n.

---

## Team examples (component breakdowns)

Native units. Full JSON: `nfl_measurement.json` / `cfb_measurement.json`.

### NFL 2025, as_of week 18

| Team | off EPA | def EPA | succ nat | pace | expl (p/r)            |  PPO | finish | ST EPA | proxy | adj off | adj def |
| ---- | ------: | ------: | -------: | ---: | --------------------- | ---: | -----: | -----: | ----: | ------: | ------: |
| BUF  |   0.120 |  −0.004 |    0.476 | 62.2 | 0.120 (0.111 / 0.128) | 2.39 |  0.425 | −0.173 | 0.109 |   0.129 |   0.011 |
| NE   |   0.148 |  −0.030 |    0.477 | 60.2 | 0.101                 |    — |      — |      — | 0.114 |       — |       — |
| SF   |   0.106 |   0.071 |    0.488 | 63.9 | 0.092 (0.087 / 0.098) | 2.21 |  0.417 | −0.109 | 0.064 |   0.137 |   0.091 |
| PHI  |   0.034 |  −0.082 |    0.431 | 58.3 | 0.099 (0.082 / 0.117) | 2.16 |  0.390 | −0.092 | 0.107 |   0.015 |  −0.123 |
| KC   |   0.067 |   0.012 |    0.457 | 61.6 | 0.094 (0.086 / 0.107) | 2.14 |  0.410 | −0.101 | 0.108 |   0.079 |   0.005 |
| NYJ  |  −0.120 |   0.132 |    0.411 | 60.1 | 0.082 (0.049 / 0.123) | 1.87 |  0.401 |  0.010 | 0.059 |  −0.136 |   0.136 |
| CLE  |  −0.194 |  −0.095 |        — |    — | —                     |    — |      — | −0.247 | 0.114 |  −0.233 |  −0.098 |

Football read (not a seal): Bills/Pats/49ers offenses sit where a 2025 board would expect. Jets offense is a hole; Browns are a bad offense / good-ish defense. Eagles defense ADJUSTED (−0.123) is stronger than raw (−0.082) after SOS. `ke.havoc` and `ke.team_strength` are empty on purpose.

**Finishing note:** NFL PPO ~2.1–2.4 and finish ~0.39–0.43 look **low** vs a typical scoring-opportunity intuition and vs CFB’s owned heuristic (Georgia 4.29 / 0.81). Likely cause: NFL points are flag-summed on `fixed_drive` and may miss FG/XP that do not share that id. Cell stays published with `points_source=nflverse_scoring_flags` for inspection — **not** filled with 3.5. A later GO can certify drive-result points. `ke.rz_td` remains the PARTIAL sibling.

### CFB 2025, as_of week 13

| Team       | off EPA | def EPA | succ nat / std | pace | expl (p/r)            |  PPO | finish | opp rate | adj off | adj def |
| ---------- | ------: | ------: | -------------- | ---: | --------------------- | ---: | -----: | -------: | ------: | ------: |
| Ohio State |   0.292 |  −0.153 | 0.575 / 0.654  | 61.6 | 0.220 (0.306 / 0.134) | 4.43 |  0.836 |    0.573 |   0.294 |  −0.188 |
| Georgia    |   0.170 |   0.026 | 0.507 / 0.598  | 70.8 | 0.212 (0.293 / 0.145) | 4.29 |  0.814 |    0.556 |   0.260 |  −0.026 |
| Oregon     |   0.175 |  −0.058 | 0.498 / 0.589  | 68.5 | 0.243 (0.316 / 0.180) | 3.65 |  0.688 |    0.589 |   0.230 |  −0.099 |
| Alabama    |   0.122 |  −0.010 | 0.453 / 0.577  | 64.5 | 0.239 (0.330 / 0.117) | 3.65 |  0.703 |    0.565 |   0.198 |  −0.065 |
| Texas      |   0.106 |  −0.079 | 0.439 / 0.551  | 64.4 | 0.233 (0.298 / 0.160) | 3.36 |  0.676 |    0.521 |       — |       — |
| Michigan   |   0.116 |  −0.017 | 0.501 / 0.586  | 65.2 | 0.211 (0.261 / 0.170) | 3.13 |  0.611 |    0.529 |   0.165 |  −0.048 |

`ke.st` OMIT. `ke.havoc` OMIT. TFL/FF/INT **DATA_INSUFFICIENT** (sparse). Sack rate is the only CFB disruption rate that cleared the 5% null-rate bar (Ohio State 4.3%, Texas 5.0%, Georgia 1.9%).

Success columns disagree (Georgia 0.507 native vs 0.598 standard). That is the #555 50/70/100 vs `EPA>0` split. Both stay. Neither is “50.”

---

## Reconcile #559 / #560 / #562

| Item                    | Phase 1 action                                                       |
| ----------------------- | -------------------------------------------------------------------- |
| #559 raw team-game defs | Reused (scrimmage, success pair, CFB expl/finish/pace)               |
| #560 ridge              | **Not** the Phase 1 ADJUSTED ID. MODELED candidate only              |
| #562 scoring            | **Not used.** Totals miss is not an explosiveness / weight ticket    |
| CFB 2026 W−1 table      | Not re-promoted; 2025 full-season PBP used for examples + validation |

---

## Worker-readable CFB PBP (platform, not vendor)

Railway still has no CFB parquet volume. This PR downloads SDV once into gitignored research cache and documents the path. **No production feature store. No compose change. No ratings promote.** A tiny copy onto a worker volume is a later platform ticket if Ryan wants live CFB measurement.

---

## How to reproduce

```bash
cd services/model-service
python3 -m pytest tests/test_ke_football_measurement.py -q

PYTHONPATH=services/model-service python3 scripts/ke_football/run_measurement_phase1.py
```

---

## STOP

Reviewable now: measurement layer, four-layer provenance, disruption inventory (no weights), PIT ADJUSTED EPA, leakage tests, validation, NFL + CFB component examples.

**Not authorized:** Team Strength composite, scoring, matchup, market, UI, board reopen, named havoc weights, #560 promote, #562 retune.
