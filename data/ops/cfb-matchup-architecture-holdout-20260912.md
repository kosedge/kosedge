# CFB matchup-architecture holdout (E1–E5)

**Generated:** `2026-09-12T18:11:30Z`  
**Production MATCHUP_RESPONSE:** `1.40` (unchanged)  
**Kill switch:** `OFF`  
**#532:** DO NOT MERGE  
**Lake:** owned Odds-API parquet 2022–24, last legal pre-kick close  
**Universe:** v1 Layer A QB + prior-year efficiency + league-average roster/units  

Frozen splits were registered **before** scoring and were not changed after:

| Split | Seasons | Role |
|---|---|---|
| Train-0 | 2022 W1–14 | registered train; not a fit target |
| Val-0 | 2023 W1–14 | first out-of-time |
| Val-1 | 2024 W1–14 | untouched holdout |

2025 sealed. 2026 / the W2 47-game DK snapshot is **not in this loss**. Close is diagnostic. Actual scores are the objective.

---

## Decision

**CAUSALITY_SUPPORTED_DO_NOT_SHIP**

Ship: **false**. Recommended coefficient: **none**.

The nonlinear composed-index matchup term causes the +10 totals bias on untouched 2022–24 data. Removing or replacing it moves location in the same direction every year. That is enough to prove the W2 diagnosis was not a 47-game fluke.

It is **not** enough to write a production coefficient.

- E1 (`r=1.00`) cuts Val-1 bias **+10.10 → +6.84**. Better, not fixed.
- Identity matchup (ratio→1) cuts Val-1 bias to **+0.09** and kills the ≥68 tail (217 → 0), but favorite-agreement vs close falls **70.8% → 61.6%**. That is a location diagnostic, not a football model.
- E3 (raw off_eff/def_eff, `r=1.00`) is the best *architecture* card: Val-1 bias **+1.13**, favorite-agreement **72.5%**. It is still sloped by projected-total bucket. Not shipped.
- E2 is a grid, not an argmin. 1.15 and 1.25 sit between E1 and 1.40. Nobody gets picked.
- E4 (possessions × linear PPP) ≈ E1. Making possessions explicit does nothing until PPP is a real drive model.
- E5 (zero HFA/coach/ST) moves Val-1 bias by **~2.0**. Same small adder we saw on W2.

Do not subtract 10. Do not optimize `|model−close|`. Do not turn the board on.

---

## Experiment cards

n is lake-only FBS–FBS with Layer A on both sides and a valid pre-kick close.

| id | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / bias / fav-agree | Val-1 close bias | tail n |
| --- | --- | --- | --- | --- | --- |
| baseline_140 | 712 / 17.471 / +11.89 | 710 / 17.793 / +12.33 | 717 / 16.651 / +10.10 / 0.708 | +11.34 | 217 |
| E1 r=1.00 | 712 / 15.248 / +7.66 | 710 / 15.638 / +8.58 | 717 / 14.871 / +6.84 / 0.711 | +8.08 | 70 |
| E2 r=1.15 | 712 / 15.920 / +9.19 | 710 / 16.343 / +9.94 | 717 / 15.463 / +8.02 / 0.712 | +9.26 | 129 |
| E2 r=1.25 | 712 / 16.480 / +10.25 | 710 / 16.883 / +10.88 | 717 / 15.910 / +8.84 / 0.714 | +10.08 | 160 |
| E0 identity | 712 / 14.116 / −1.05 | 710 / 13.744 / +0.78 | 717 / 13.260 / +0.09 / **0.616** | +1.33 | 0 |
| E3 raw O/D r=1.40 | 712 / 15.813 / +2.65 | 710 / 16.772 / +4.28 | 717 / 15.842 / +2.47 / 0.714 | +3.71 | 122 |
| E3 raw O/D r=1.00 | 712 / 14.498 / +0.90 | 710 / 14.965 / +2.61 | 717 / 14.432 / **+1.13** / **0.725** | +2.37 | 54 |
| E4 poss×PPP | 712 / 15.318 / +7.88 | 710 / 15.722 / +8.75 | 717 / 14.946 / +6.98 / 0.713 | +8.22 | 76 |
| E5 zero adders | 712 / 16.469 / +9.85 | 710 / 16.890 / +10.30 | 717 / 15.718 / +8.06 / 0.676 | +9.30 | 164 |

Dose-response on Val-1 actual bias is monotone: **1.40 +10.10 > 1.25 +8.84 > 1.15 +8.02 > 1.00 +6.84 > identity +0.09**. That is the exponent doing what the W2 ledger said it would do.

Favorite flips vs close barely move under E1 (209 → 207). On this reconstructed universe the exponent inflates **totals** more than it flips sides. Live 2026 W2 (real roster/QB, wider ratios) is the regime where the same term also flips favorites. Both facts can be true.

---

## Year stability (baseline vs E1)

| season | baseline bias / MAE / fav-agree | E1 bias / MAE / fav-agree |
| --- | --- | --- |
| 2022 | +11.89 / 17.47 / 0.754 | +7.66 / 15.25 / 0.757 |
| 2023 | +12.33 / 17.79 / 0.753 | +8.58 / 15.64 / 0.766 |
| 2024 | +10.10 / 16.65 / 0.708 | +6.84 / 14.87 / 0.711 |

Same direction every year. Not a 2024 one-off. Not a W2 one-off.

---

## Calibration by projected total (Val-1)

Baseline 1.40 is a slope, not a constant +10:

| predicted | n | bias vs actual |
| --- | ---: | ---: |
| <48 | 15 | −4.60 |
| 48–54 | 67 | +1.49 |
| 54–60 | 154 | +5.61 |
| 60–68 | 264 | +9.32 |
| ≥68 | 217 | **+17.91** |

E3 raw O/D at `r=1.00` is the least drunk mean, and still sloped:

| predicted | n | bias vs actual |
| --- | ---: | ---: |
| <48 | 156 | −7.97 |
| 48–54 | 194 | −2.05 |
| 54–60 | 169 | +2.49 |
| 60–68 | 144 | +9.13 |
| ≥68 | 54 | +13.32 |

A −10 haircut would still misprice both tails. E3 is the next architecture to design against, not a number to ship.

---

## What each experiment proved

1. **E1** — `MATCHUP_RESPONSE=1.00` is a real ablation. It removes ~3–4 points of actual bias every year and collapses the ≥68 tail 217 → 70. Leftover +6.8 on Val-1 is the composed-index location (QB/O>D) still sitting inside the ratio.
2. **E2** — 1.00 / 1.15 / 1.25 / 1.40 is a dose-response, not a search. No interior minimum that earns 1.15 or 1.25.
3. **E3** — calculating the ratio from raw off_eff/def_eff, not composed `off_idx`, is the first architecture that jointly cools the mean **and** keeps favorite identity. Residual slope means we still need a better interaction (and eventually E4 for real).
4. **E4** — `12.6 × pace × linear PPP` ≈ E1. Possessions are not the current failure. A drive/finishing model is still the long-term totals path; it is not what fixes +10 today.
5. **E5** — adders are ~2 points. Do not confuse them with the drunk term.

---

## What this is not

- Not a production coefficient change.
- Not a −10 totals haircut.
- Not a fit to the W2 47-game DK snapshot.
- Not permission to turn the board on.
- Not a claim that identity matchup is a model.

Next design work, if any: a **raw O/D interaction** that is not `composed_index ** 1.40`, specified before it is fit, scored on these same frozen splits. Until that exists, CFB stays dark.
