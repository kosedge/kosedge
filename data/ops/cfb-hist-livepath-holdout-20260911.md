# CFB historical Week-0 reconstruct + totals experiment (STOP)

**Date:** 2026-09-11  
**Branch:** `cursor/cfb-hist-roster-holdout-1bf8`  
**After:** #536 merged KEEP DARK; #537 diagnostic (matchup-response on the sum)  
**Kill switch:** `CFB_EDGE_BOARD_PUBLIC_ENABLED = false` — **unchanged**  
**Production model:** **not modified.** No λ. No coefficient. No PLAY. No 2026 W1/W2 fit.

2025 residuals were **never opened**. There is no freeze file.

---

## Verdict

**STOP. Do not fit λ. Do not open 2025. Do not propose a production coefficient.**

The +8 to +10 2026 totals inflation **does not exist** on the reconstructable historical path. 2023–24 W0–2 frozen (hist-cal identity + SDV close), n=253:

| Predictor | Mean bias vs close | MAE | RMSE | vs actual MAE |
|---|---:|---:|---:|---:|
| Frozen model | **−0.46** | 5.56 | 7.02 | 13.83 |
| Matchup neutralized | +1.61 | 5.88 | 7.23 | 13.33 |
| Market close (baseline) | 0 by construction | 0 | 0 | 12.61 |
| Sum-only dampen (b) | *not fit* | — | — | — |
| Level offset (a) | *not fit* | — | — | — |

Mean matchup inflation on that path: **−2.07** (threshold to even consider a fit was +6). Neutralizing matchup *worsens* close MAE. Shipping (b) from this table would be fitting a cure for a disease that is not in the historical data.

The 2026 +10 is **unique to the live 2026 roster/QB/unit compose**, not a missing historical intercept and not SP+ acting alone.

---

## 1. Reconstructed-data audit

Same-path lock: 2026 live = ESPN roster + QB + units **recruiting-anchored** + **Connelly SP+ carry**.

| Field | Status | What we did |
|---|---|---|
| ESPN core athletes, year-locked | **Reconstructable** | `seasons/{Y}/teams/{id}/athletes`. Smoke ALA: 242 (2023) / 182 (2024) / **177 (2025)** / 100 (2026 live pack). 2025 lists exist and are year-locked; they are not a 2026 recruiting/SP+ substitute. |
| Site roster `?season=Y` | **Forbidden** | Ignores year; returns the current 2026 club. |
| Connelly SP+ 2022–2024 finals | **Missing** | CFBD 401. ESPN Insider HTML has 0 `<tr>`. 2025 final is public (already the 2026 carry). Must not reuse 2025 SP+ as a 2023–25 prior. |
| SDV `cfb_ratings` adj EPA | **Available, not SP+** | Used for 2023–24 efficiency. Labeled. |
| Recruiting capital | **Unminted** | 2026 priors would be a future leak. CFBD `/recruiting/teams` keyed. |
| Portal teamHistory | **Unminted** | 2026 pack is already incomplete on outflow. |
| QB prior-year attempts | **Unminted** | Class from experience abbr only. |
| Coaching flags | **Unminted** | Assume returning. Do not copy 2026 staff. |
| HFA buckets | 2026 venue prior, labeled | Venues persist; not an efficiency leak. |
| CFBD key | **Absent** | |

Full field table: `src/services/cfb_season_engine/hist_week0.py`  
Year-lock smoke: `data/ops/cfb-hist-week0-smoke/year-lock-counts.json`

A packager exists (`scripts/cfb/package_historical_week0_state.py`) that writes year-locked athletes and **leaves unit talent at 50**. That is honest. It is **not** the 2026 live stack, because 2026 unit talent is `0.62 * recruiting + …` and we refuse to copy 2026 recruiting onto 2023–25.

2025 Week-0 *inputs* were audited the same way (year-locked ESPN lists exist). **2025 residuals were not scored.** Reconstructing the 2025 roster list is not opening the 2025 holdout.

---

## 2. Experiment design (as run)

```text
1. Inventory fields. Refuse silent 2026 substitutes.
2. Score 2023–24 W0–2 only. 2025 sealed (no freeze file → hard fail if --open-2025).
3. Ask: does mean matchup inflation ≥ +6 (the 2026 shape)?
   NO  → STOP. Do not fit λ. Do not open 2025.
   YES → fit λ and offset on 2023–24 only, write freeze, then open 2025.
4. 2026 W1/W2 books are confirmatory ablation only — never a training set.
```

Comparators (when a fit is allowed): frozen · matchup-neutralized · sum-only (b) · level-offset (a) · market close.  
(b) is sum-only: `kei_total = T0 − (1−λ)·inflation`. Spread identity checked (`spread_identity_violations = 0`).

2025 seal test: `tests/test_cfb_hist_week0_seal.py`.

---

## 3. Frozen thresholds

**None.** No freeze file. `lambda_b = null`. `level_offset_a = null`.

We did not look at 2025 residuals to “see if 0.54 works.”

---

## 4. Historical results (2023–24 W0–2, n=253)

Path actually scored: `hist_cal_league_avg_fallback_no_recon_pack`  
(full recon packs not written — smoke was 6 teams only, moved out of the engine data dir so a mixed 6-team universe could not pretend to be complete.)

This is the same identity hist-cal already graded: league-avg roster/QB/units + prior-year SDV adj-EPA.

### Headlines

- Frozen vs close: **slightly Under** (mean −0.46 / median −0.34), MAE 5.56, RMSE 7.02; 120 Over / 132 Under  
- Frozen vs actual: mean −0.23, MAE 13.83, RMSE 17.25  
- Market vs actual MAE 12.61 / RMSE 15.56 — books beat the model on realized scoring, with no Over-drunk model shape  
- Matchup inflation **−2.07**  
- Neutralizing matchup **hurts** close MAE/RMSE (+0.32 / +0.21) and flips the mean residual to +1.61  
- Sum-only (b) and level-offset (a): **not fit** (`lambda_b = null`)  
- Spread identity on the sum-only transform (λ=0.5 identity check on scored rows): **0 violations**

### Error tails (frozen vs close)

| | p90 \|err\| | p95 \|err\| | max \|err\| | share >10 | share >15 |
|---|---:|---:|---:|---:|---:|
| vs close | 11.95 | 13.81 | 20.27 | 16.2% | 3.6% |
| vs actual | 28.42 | 32.63 | 55.23 | 55.3% | 39.1% |

Realized-score tails are large because early-season totals are noisy. Close-line tails are not a +10 systematic Over.

### Calibration by predicted-total bucket (frozen vs close)

| Bucket | n | mean | MAE |
|---|---:|---:|---:|
| <48 | 70 | **−4.77** | 6.13 |
| 48–52 | 68 | −0.40 | 5.18 |
| 52–56 | 59 | +1.49 | 5.66 |
| 56–60 | 27 | +2.10 | 4.68 |
| ≥60 | 29 | **+3.44** | 5.71 |

The high bucket is +3.4, not +10. The low bucket is Under — opposite of 2026 live.

### Week

| Week | n | mean | MAE | RMSE |
|---|---:|---:|---:|---:|
| W1 | 153 | +0.20 | 5.20 | 6.74 |
| W2 | 100 | **−1.48** | 6.12 | 7.43 |

2023–24 W2 is slightly Under. 2026 W2 is +10 Over. Same week window, opposite sign.

### Matchup family (2026 affiliation map; 2023 Pac-12 labeled by that map)

| Family | n | mean | MAE |
|---|---:|---:|---:|
| P4 vs P4 | 81 | −0.59 | 5.50 |
| P4 vs G5 | 99 | −0.94 | 5.17 |
| G5 vs G5 | 73 | +0.32 | 6.17 |
| peer \|spread\|<10 | 194 | −0.68 | 5.79 |
| cupcake \|spread\|≥17 | 10 | +1.44 | 4.65 |

No family on this path is +8 to +10.

**The +8 to +10 2026 phenomenon is not in 2023–24 on this path.**

---

## 5. What is unique about 2026 (confirmatory ablation)

Same frozen formula, same W1+W2 confirmatory books (n=90). Not a fit.

| Variant | Mean T resid | Matchup inflation | Off-index SD | Mean \|spread\| |
|---|---:|---:|---:|---:|
| Frozen (live roster + SP+) | **+9.14** | +8.08 | 0.188 | 12.98 |
| League-avg roster, **keep SP+** | **+0.10** | −1.25 | 0.100 | 8.36 |
| Keep live roster, **explicit 50 efficiency** | +7.18 | +6.24 | 0.112 | 7.19 |
| Both league | −1.60 | −2.83 | 0.000 | 1.97 |

`build_efficiency_profile(None)` reloads packaged 2025 SP+ for official FBS. The efficiency-off variant uses an **explicit** 50 payload so it does not silently keep SP+.

Reading:

1. **SP+ alone does not create the +10.** Put live SP+ on league-avg roster/QB/units and the W1/W2 gap collapses to +0.1 — the hist-cal shape.  
2. **Live 2026 roster/QB/units create most of it.** Zero SP+ and keep the 2026 compose: still **+7.2**.  
3. That compose is not “who is on the roster.” 2026 `unit_grades_from_roster` is **0.62 recruiting-anchored**. Class-year ESPN lists without recruiting flatten toward 50 — which is why a year-locked athlete reconstruct *cannot* reproduce 2026 width without a year-specific recruiting pack we do not have.  
4. `MATCHUP_RESPONSE=1.40` (W2 effective 1.30) then turns that width into sum inflation. Hist-cal raised the exponent to decompress spreads on a *narrow* identity. Live 2026 is a wide identity under the same exponent.

So 2026 is not “the intercept drifted.” It is **recruiting-anchored unit/QB width × an exponent calibrated on league-avg identity.**

---

## 6. Why we still do not ship a haircut

A λ fit on 2023–24 would learn “don’t dampen” / “dampen the wrong way” (inflation is negative). Applying that, or a 2026-street λ, to production:

- would not be unused-2025 same-path evidence  
- would be fitting the confirmatory board the user told us not to optimize  
- would couple to spreads if anyone “just” cuts `MATCHUP_RESPONSE`

Unblock, later, if someone wants a *real* same-path holdout:

1. CFBD (or a committed archive) of **final SP+ 2022, 2023, 2024**  
2. Year-specific **recruiting** packs for 2023–25 (not 2026 priors)  
3. Rebuild Week-0 identity with those two fields  
4. Only then: look at 2023–24 inflation; if it is +8-ish, freeze λ; **then** open 2025  

Until that exists, public CFB stays dark because the live totals mechanism has not earned an OOS green — not because the board is scary.

---

## 7. Spreads

Pre-registered historical slices (G5@P4 cupcakes, service academies, negative-carry brand, open-comp QB) were **not** run as a retune. The six 2026 outliers were not used as a loss. Sum-only candidate (when it exists) is proven spread-identity-preserving on the 2023–24 rows we scored (`violations = 0`). No spread coefficient is proposed.

---

## 8. 2026 W1/W2 actuals

Not settled as a locked grade file in this pass. When they are, grade **frozen vs actual** and (if a freeze ever exists) the frozen candidate — confirmatory, not a fit.

---

## File index

| Path | Role |
|---|---|
| `hist_week0.py` | Field audit + 2025 seal |
| `package_historical_week0_state.py` | Year-locked ESPN core packager (recruiting unminted) |
| `run_hist_livepath_totals.py` | 2023–24 only; refuses 2025 without freeze |
| `cfb_2026_identity_ablation.py` | Confirmatory 2026 uniqueness |
| `test_cfb_hist_week0_seal.py` | Seal + no-live-path asserts |
| `cfb-hist-livepath-totals-20260911.json` | Historical numbers |
| `cfb-2026-identity-ablation-20260911.json` | Ablation numbers |
