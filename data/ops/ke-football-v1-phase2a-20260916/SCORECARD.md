# KE Football v1 — Phase 2A unit rating scorecard

**Status:** `LOCKED` · `UNIT_MEASUREMENT_PARTIAL_V1` · `production_promote=false`
**Version id:** `ke-football-v1-unit-measurement-partial-2026-09-16`
**Ryan (2026-09-16):** FINAL LOCK. Phase 2A accepted as **PARTIAL v1**. No Phase 2B.
**Lock:** `docs/ratings/KE_FOOTBALL_V1_UNIT_MEASUREMENT_PARTIAL_LOCK_2026-09-16.md`
**STOP:** Team Strength, overall weights, matchup, scoring, market, ATS, UI, boards, opp-adj reopen. No retune of `k`.

`NO_ADJUSTMENT_WINNER` held. Unadjusted trailing EPA is the baseline.
Complexity did not earn inclusion. That does **not** by itself validate shrinkage.

Numbers below are from frozen `nfl_phase2a.json` / `cfb_phase2a.json` (no refit). Companion: `baseline_comparison.json`.

### Ryan PARTIAL amend (docs only — no refit)

| # | Required | Lock |
| - | -------- | ---- |
| 1 | Trailing vs shrunken MAE per unit (Δ, %, n, uncertainty) | Confirmation: NFL off −0.54% / def −0.34% (n=214); CFB off −2.04% / def −2.33% (n=446). MAE SE / bootstrap **missing**. |
| 2 | `k=160` before frozen confirmation | 2025 only; next-game EPA/play MAE; NFL weeks 5–10 (n=170); CFB weeks 4–8 (n=577); grid cap 160; no folds. Confirmation **not** used to pick k. |
| 3 | Exact formula + defensive sign | Trailing EPA **not** league-centered. `μ + n/(n+160)×(EPA − μ)`. Defense = EPA allowed, **lower better** (not flipped). |
| 4 | `n/(n+k)` label | Shrinkage weight / sample-strength. **Not** calibrated uncertainty / SE / CI. |
| 5 | PARTIAL permit vs forbid | Research unit measurement only. Forbids Team Strength, public KE, scoring/market/ATS, boards, opp-adj reopen, Phase 2B. Frozen `scorecard.json` still has `phase2b_eligible=true` from the run — **superseded**; Phase 2B is forbidden. |

---

## Definition

```text
w = n / (n + 160)                                 # shrinkage weight / sample-strength
unit = μ + w × (EPA_trailing − μ)
```

Trailing EPA is play-weighted, **not** league-centered. `μ` is the unweighted mean of teams' trailing EPA at as_of W (`week < W`).

| Side | Native unit | Better |
| --- | --- | --- |
| `ke.off_unit` | EPA per play | **higher** |
| `ke.def_unit` | EPA **allowed** per play | **lower** (not flipped) |

`w` is **not** a confidence interval, SE, or calibrated uncertainty.

---

## Trailing vs shrunken (the comparison that must be explicit)

Δ = shrunken − trailing. Negative = shrinkage better. MAE SE / bootstrap: **missing** (residuals not persisted).

### Frozen confirmation (sealed; k already locked)

| Unit | n | Trailing MAE | Shrunken MAE | Abs Δ | Rel % |
| --- | ---: | ---: | ---: | ---: | ---: |
| NFL off | 214 | 0.16435 | 0.16346 | −0.00090 | **−0.54%** |
| NFL def | 214 | 0.16499 | 0.16442 | −0.00057 | **−0.34%** |
| CFB off | 446 | 0.17226 | 0.16875 | −0.00351 | **−2.04%** |
| CFB def | 446 | 0.17626 | 0.17215 | −0.00411 | **−2.33%** |

NFL confirmation move is well under 2%. CFB is about 2%. Point estimates only.

### Selection window (where k was chosen)

| Unit | n | Trailing MAE | Shrunken MAE | Abs Δ | Rel % |
| --- | ---: | ---: | ---: | ---: | ---: |
| NFL off | 170 | 0.18131 | 0.17679 | −0.00451 | −2.49% |
| NFL def | 170 | 0.19682 | 0.18874 | −0.00808 | −4.11% |
| CFB off | 577 | 0.17694 | 0.17067 | −0.00627 | −3.54% |
| CFB def | 577 | 0.18808 | 0.17361 | −0.01447 | −7.70% |

---

## Shrinkage selection

| | |
| --- | --- |
| Season | 2025 only |
| Folds | none (no nested holdout) |
| Grid | `{0, 20, 40, 80, 160}` — 160 is the cap |
| Objective | next-game EPA/play MAE |
| NFL selection | weeks 5–10 |
| CFB selection | weeks 4–8 |
| Confirmation | NFL 11–18; CFB 9–13 — **not used to pick k** |
| Per-k table persisted? | **no** (only winning `shrink_k_selection_mae`) |

**Peek:** confirmation MAE was used to **label** the published winner `epa_shrunken` vs trailing. That is a label peek, not a k peek.

---

## Method bakeoff (complexity did not earn)

A composite needed ≥2% confirmation MAE vs the strongest constituent on **both** sides. None did.

### NFL 2025 as_of 18 — confirmation n=214

Off winner: `epa_shrunken` · Def winner: `epa_shrunken` · k=160

| Method | Off MAE | Off r | Def MAE | Def r | Beats trailing 2%? |
| --- | ---: | ---: | ---: | ---: | --- |
| epa_raw (trailing) | 0.164 | 0.296 | 0.165 | 0.282 | baseline |
| epa_shrunken | 0.163 | 0.292 | 0.164 | 0.282 | no (see Δ table) |
| z_pass | 0.164 | 0.298 | 0.167 | 0.258 | no |
| z_earned | 0.164 | 0.298 | 0.170 | 0.230 | no |
| pca_earned | 0.193 | 0.303 | 0.180 | 0.239 | no |
| ridge_earned | 0.163 | 0.313 | 0.170 | 0.159 | no |

Earned PARTIAL features: off none; def `expl_allowed`, `disruption_proxy_nfl` (selection only — lost confirmation). Finishing not earned.

### CFB 2025 as_of 13 — confirmation n=446

| Method | Off MAE | Off r | Def MAE | Def r | Beats trailing 2%? |
| --- | ---: | ---: | ---: | ---: | --- |
| epa_raw (trailing) | 0.172 | 0.339 | 0.176 | 0.286 | baseline |
| epa_shrunken | 0.169 | 0.341 | 0.172 | 0.322 | ~2% (see Δ table) |
| z_pass | 0.173 | 0.319 | 0.176 | 0.286 | no |
| z_earned | 0.173 | 0.319 | 0.175 | 0.292 | no |
| pca_earned | 0.285 | 0.320 | 0.185 | 0.292 | no |
| ridge_earned | 0.173 | 0.318 | 0.173 | 0.293 | no |

Earned PARTIAL features: off none; def `success_allowed` (selection only). Finishing not earned.

---

## PARTIAL v1 — permit vs forbid

Canonical lock: `docs/ratings/KE_FOOTBALL_V1_UNIT_MEASUREMENT_PARTIAL_LOCK_2026-09-16.md`.

| Permits | Does NOT permit |
| --- | --- |
| Research team-week unit measurement | Production promotion |
| Internal ranking / sanity | Customer-facing KE Off/Def Efficiency |
| Component comparison | Team Strength |
| Continued OOS validation | Scoring-model replacement / integration |
| Candidate input in future *separately authorized* research | Matchup or market integration |
| | Board reopening |
| | Claims of calibrated uncertainty |
| | Claims that shrinkage materially or statistically beats trailing EPA |
| | Retuning `k=160` against confirmation |
| | Phase 2B |

Trailing EPA remains the explicit baseline alongside every evaluation of the shrunken measurement.

**Unvalidated:** shrinkage vs trailing without MAE SE; single-season grid-cap k; missing per-k table; label peek on confirmation; no earned latent composite.

Narrative: `docs/ratings/KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md`.
