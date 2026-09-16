# LOCKED — KE Football v1 unit measurement (PARTIAL)

**Status:** `LOCKED` · `UNIT_MEASUREMENT_PARTIAL_V1` · `production_promote=false`
**Version id:** `ke-football-v1-unit-measurement-partial-2026-09-16`
**Date:** 2026-09-16
**PR:** #570
**Ryan:** FINAL LOCK. Phase 2A accepted as **PARTIAL v1**. No phase advance.

Machine freeze: `data/ops/ke-football-v1-phase2a-20260916/PARTIAL_V1_LOCK.json`
Narrative: [`KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md`](./KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md)

This file is the v1 definition. Later evidence may accumulate **beside** it. Later evidence may **not** silently change the formula, `k`, orientation, or permit/forbid below.

---

## Accepted frozen formulation

```text
unit = μ + [n / (n + 160)] × (EPA − μ)
```

Equivalent: `w × EPA + (1 − w) × μ` with `w = n/(n+160)`.

| Symbol         | Meaning                                                            |
| -------------- | ------------------------------------------------------------------ |
| `EPA`          | Trailing play-weighted EPA, `week < W`. **Not** league-centered.   |
| `μ`            | Unweighted mean of teams' trailing EPA at as_of `W` (PIT).         |
| `n`            | Trailing scrimmage plays on that side (`off_epa_n` / `def_epa_n`). |
| `k`            | **160** (plays). Frozen. Do not retune against confirmation.       |
| Layer          | DERIVED                                                            |
| `opp_adj_used` | `false` (`NO_ADJUSTMENT_WINNER` held)                              |

`k=160` was selected **exclusively** on the documented 2025 selection windows. Confirmation is **excluded** from parameter selection.

| Sport | Season   | Selection (k chosen here)        | Confirmation (sealed; not used for k) |
| ----- | -------- | -------------------------------- | ------------------------------------- |
| NFL   | 2025 REG | weeks **5–10**, n=170 team-games | weeks **11–18**, n=214                |
| CFB   | 2025     | weeks **4–8**, n=577 team-games  | weeks **9–13**, n=446                 |

Objective at selection: next-game EPA/play MAE. Grid `{0, 20, 40, 80, 160}` (160 is the cap). **No folds. No other season.** Do **not** retune `k=160` against confirmation.

Code: `shrink()` in `services/model-service/src/services/ke_football/unit_ratings.py` (`w * value + (1 - w) * league`).

---

## Native orientation (preserved)

| Side                    | Native unit               | Better                  |
| ----------------------- | ------------------------- | ----------------------- |
| Offense (`ke.off_unit`) | EPA **produced** per play | **higher**              |
| Defense (`ke.def_unit`) | EPA **allowed** per play  | **lower** (not flipped) |

---

## `n/(n+k)` label

`n/(n+160)` is a **shrinkage / sample-strength weight only**.

It is **not** a probability, confidence, calibrated uncertainty, standard error, or confidence interval.

---

## Confirmation evidence (directional only)

Δ = shrunken MAE − trailing MAE. Negative = shrinkage better on the point estimate. Trailing EPA remains the **explicit baseline** beside every evaluation of the shrunken measurement.

| Unit        |   n | Rel % (confirmation) |
| ----------- | --: | -------------------: |
| NFL offense | 214 |           **−0.54%** |
| NFL defense | 214 |           **−0.34%** |
| CFB offense | 446 |           **−2.04%** |
| CFB defense | 446 |           **−2.33%** |

Do **not** characterize as statistically established. MAE SE / bootstrap is **unavailable**. Do **not** claim that shrinkage materially or statistically beats trailing EPA.

---

## PARTIAL v1 permits

- Research team-week unit measurement
- Internal ranking / sanity
- Component comparison
- Continued OOS validation
- Use as a **candidate input** in future _separately authorized_ research

## PARTIAL v1 does NOT permit

- Production promotion
- Customer-facing KE Off/Def Efficiency
- Team Strength
- Scoring-model replacement or integration
- Matchup or market integration
- Board reopening
- Claims of calibrated uncertainty
- Claims that shrinkage materially or statistically beats trailing EPA
- Retuning `k=160` against confirmation
- Phase 2B

Preserve trailing EPA as the explicit baseline alongside every evaluation of the shrunken measurement.

---

## Next (not this PR)

Evidence only:

- Add uncertainty around the MAE delta when feasible
- Accumulate strictly OOS observations

Do **not** retune `k=160` against confirmation. Do **not** advance phases on this PR.

---

## Freeze — version id + checksums

**Version id:** `ke-football-v1-unit-measurement-partial-2026-09-16`

SHA-256 of the frozen method and scorecard artifacts (bytes as of this lock). Subsequent evidence must not replace these files in place. New evidence gets a new path.

| Artifact                                                            | SHA-256                                                            |
| ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `services/model-service/src/services/ke_football/unit_ratings.py`   | `5d48a28137c69f127ff2ebd7602c6e144c597ea6d885f4eef8f6e4f1ec19634f` |
| `data/ops/ke-football-v1-phase2a-20260916/scorecard.json`           | `ec7f0747215c38ba9d0b3f1a1691217a89a6485d505b51f8d0477af579b8763a` |
| `data/ops/ke-football-v1-phase2a-20260916/baseline_comparison.json` | `7522e84126a06a7e9501658737941883a3071fc81ad5c07d9321a3ac66d8584c` |
| `data/ops/ke-football-v1-phase2a-20260916/nfl_phase2a.json`         | `de1c5c3ed1b00d61e3eada82c32400910daec4c52341b8281a622798f61eeced` |
| `data/ops/ke-football-v1-phase2a-20260916/cfb_phase2a.json`         | `81cd20d29dc207013ee7c096764df31fa09e1173d1aa0458c0de2752b164bea5` |

Frozen `scorecard.json` still carries `phase2b_eligible=true` from the run. That field is **superseded** by this lock. Phase 2B is forbidden.

---

## STOP

No Phase 2B. No retune of `k`. No Team Strength / scoring / boards / ATS.
