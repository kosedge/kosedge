# CFB model diagnostic — totals inflation + spread outliers (research only)

**Date:** 2026-09-11  
**After:** #536 merged to `deploy-vercel` (`61e339fb`) — packaging + fail-closed `NAME_TO_CODE`.  
**Kill switch:** `CFB_EDGE_BOARD_PUBLIC_ENABLED = false` — **unchanged. Public CFB stays dark.**  
**Production model:** **not modified.** No coefficient, clamp, shrink, Vegas, PLAY, or KEI-guard edit.

Harness: `scripts/cfb/cfb_model_total_diagnostic.py`  
Artifact: `data/ops/cfb-model-diagnostic-20260911.json`

This pass treats remaining residuals as **genuine model-vs-market behavior**. Markets are evaluation benchmarks, not training answers.

---

## Merge receipt

| Item | Status |
|---|---|
| #536 squash-merge | `61e339fb` on `deploy-vercel` |
| Public kill switch | still hardcoded `false` (web + model-service) |
| Totals PLAY | still sat |
| Spread PLAY | still sat |
| `kei_total` | still identity of `model_total` |
| Odds ingest / NFL / Line Curve | untouched |

Do not treat this merge as CFB reactivation.

---

## Verdict (read this first)

**Totals +9 to +10 is not a formula bug.**  
`model_total` reconstructs from stored diagnostics to **0.009 pts**. There is no duplicated adder, no sign error, no missing clamp, and no bad intercept.

**The bias is almost entirely `(off/def)^MATCHUP_RESPONSE` on the live 2026 identity stack.**

On W2 FBS–FBS (n=47, ESPN/DK 2026-09-11):

| Path | Mean model total | Gap vs street (53.07) |
|---|---:|---:|
| Frozen model (actual) | 63.02 | **+9.94** |
| Neutralize matchup ratio → 1 | 54.08 | **+1.01** |
| Neutralize unit offense boost | 62.09 | +9.01 |
| Neutralize unit defense dampen | 64.13 | +11.06 (dampen was cooling) |
| Neutralize pace | 62.83 | +9.76 |
| Neutralize HFA+coach+ST | 60.75 | +7.68 |
| `2 × LEAGUE_TEAM_PPG` (51.8) | 51.80 | **−1.27 vs street** |

W1 (handicap card, n=43) repeats the same shape: actual **+8.25** → matchup-off **+1.12**.

Classification: **legitimate misspecification of the matchup-exponent × real-roster/SP+ width interaction.**  
Not a data-mapping leftover. Not a silent `1.0` hydrate. Not something to fix by subtracting 9–10 points or fitting this week’s books.

**Do not twist knobs on these 47 games.** Proposed experiments are below. None of them are authorized for production.

---

## 1. How `model_total` is built (every term)

Frozen path (`team_projection.expected_team_points` → `project_game`):

```text
pts_side = LEAGUE_TEAM_PPG * (off_idx / def_idx)^response
         * unit_offense_boost * opp_unit_defense_dampen * pace
         + variable_HFA + coaching_week_adj
pts_side = clamp(pts_side, 7, 55)
total    = home_pts + away_pts + special_teams_nudge
kei_total := model_total          # identity — no totals guard
```

Live constants:

| Knob | Value | Notes |
|---|---|---|
| `LEAGUE_TEAM_PPG` | 25.9 | Hist-cal 2026-08-05 cut from 27.5 |
| `MATCHUP_RESPONSE` | 1.40 | Hist-cal raised from 1.22 to decompress spreads |
| Effective response W1 / W2 | **1.26 / 1.302** | Early soften 0.90 / 0.93 |
| Ratio clamp | (0.52, 1.45) + 42% excess retain | Soft, not a hard cap |
| Unit boost / dampen scales | 0.07 / 0.09 | Small vs matchup |
| ST nudge | ~+0.19 mean | Noise |
| Early uncertainty | widens `margin_sd` only | **Does not haircut PPG** |

Identity inputs (compose): 2025 SP+ carry (`EFF_CARRY_SHRINK=0.85`) + 2026 ESPN roster / QB / units + coaching. Hist-cal graded the same exponent on **league-average** roster/QB proxies — a narrower O/D distribution.

Reprojection of the packaged universe matches the published KEI pack (W2 mean total 63.02; residual audit mean +9.94 / median +9.14 unchanged). Reconstruct error **0.009**.

---

## 2. Where the +10 comes from

### Mechanism

On a real 2026 roster the favorite’s `off/def` ratio is wide. Raising it to `^1.30` lifts that side’s scoring a lot. The dog’s ratio is nearer 1 (or still >0.9 after the exponent), so the dog still prints near-league points. **Sum inflates. Street does not.**

W2 mean matchup factors (already `ratio^response`): home **1.241**, away **1.097**. Average > 1 is the whole story — both sides get a scoring lift more often than a suppression.

W2 matchup-inflation vs total residual: **r = 0.71**.

Loud examples (not used to fit anything):

| Game | Model T | Market T | Resid | Matchup inflation | Mean matchup factor |
|---|---:|---:|---:|---:|---:|
| UTSA@TXST | 85.78 | 66.5 | +19.3 | **+30.5** | 1.57 |
| UNLV@UNT | 77.91 | 57.5 | +20.4 | +21.0 | 1.38 |
| DUKE@ILL | 73.78 | 51.5 | +22.3 | +17.8 | 1.33 |
| USF@ARMY | 67.81 | 46.5 | +21.3 | +12.6 | 1.24 |
| APP@ECU | 53.83 | 56.5 | **−2.7** | +0.2 | 1.00 |
| SDSU@UCLA | 50.27 | 54.5 | **−4.2** | −1.0 | 0.98 |

The two W2 unders are the games where matchup inflation is ~0 or negative. That is the control the rest of the slate lacks.

### Discarded hypotheses

| Hypothesis | Evidence | Keep? |
|---|---|---|
| Formula / units / double-count adder | Reconstruct 0.009; boost×dampen net ~0.99 | No |
| Bad intercept / PPG too high | `2×25.9=51.8` is **1.3 under** W2 street | No |
| Pace / explosiveness explosion | Mean pace 1.002; neutralize pace **−0.18** | No |
| Preseason prior / power-SoT fill | Fill count this run = 0; P0 power finite | No |
| Feature drift from #536 mapping | Bias existed W1 (+8.3) before P0 mattered; RUT/BC unchanged | No |
| Silent null-power hydrate | Fail-closed; 0 null power | No |
| KEI totals guard leftover | There is no totals branch; `kei_total ≡ model_total` | Expected |
| “Just cupcakes” | Peer `\|spread\|<10` still **+8.0** (n=39) | No |
| “Just G5@P4” | P4@P4 **+9.5** (n=24); G5@G5 **+9.1** (n=20) | No |

Fast-pace bucket looks radioactive (+16.9, n=12) **because** `pace ≈ 1 + (skill−front_seven)/200`. That is the same identity width that feeds O/D ratios. Neutralizing the pace **term** does nothing; neutralizing matchup removes the bias. Pace is a correlate, not the cause.

Returning-production / continuity: live pack scores cluster **≥60** on every joined game (n=90). No slice. Available as a feature, not informative this week.

### Why hist-cal didn’t prevent this

Hist-cal (2026-08-05) on league-avg roster/QB:

- Totals vs close bias **+3.23 → −0.48** by cutting PPG 27.5→25.9
- Spreads were compressed, so `MATCHUP_RESPONSE` **1.22 → 1.40**

That pair is internally consistent **on the proxy path**. Unused 2025 proxy holdout identity gap on W0–2 is **+0.20** (`data/ops/cfb-totals-guard-holdout-20260903.md`). The +10 does **not** appear until live ESPN roster + SP+ carry widens ratios under the same exponent.

So: intercept is fine; the interaction term is not transportable from proxy identity to live identity.

A real-roster unused-2025 twin holdout is still **blocked** (`data/ops/cfb-totals-guard-real-roster-holdout-blocker-20260903.md`): no 2023–25 Week-0 roster/SP+ packs. Do not mix proxy-fit `λ≈0.54` onto live 2026.

---

## 3. Calibration slices (joined W1+W2, n=90)

Market sources: W1 = 2026-08-31 handicap card; W2 = ESPN/DK 2026-09-11. Not a close-lock. Good enough to locate the bias; not good enough to fit a guard.

| Slice | n | Mean T resid | T MAE | Mean matchup inflation |
|---|---:|---:|---:|---:|
| W1 | 43 | +8.25 | 8.54 | +7.14 |
| W2 | 47 | +9.94 | 10.24 | +8.94 |
| Peer `\|s\|<10` | 39 | +7.99 | 8.32 | +6.76 |
| Cupcake `\|s\|≥17` | 27 | +10.43 | 10.63 | +9.86 |
| Model total ≥64 | 32 | **+14.96** | 14.96 | +14.26 |
| Model total 48–52 | 6 | +0.62 | 2.45 | −2.41 |
| Fast pace >1.03 | 12 | +16.90 | 16.90 | +16.19 |
| Slow pace <0.97 | 17 | +5.07 | 5.33 | +5.94 |
| Hot offense idx ≥1.15 | 63 | +11.02 | 11.06 | +9.58 |
| Mid offense | 26 | +4.74 | 5.65 | +4.71 |
| Home favorite (mkt) | 70 | +9.43 | 9.78 | +8.39 |
| Home dog (mkt) | 19 | +7.72 | 7.81 | +6.84 |
| Service academy | 2 | +12.83 | 12.83 | +10.65 |
| P4@P4 | 24 | +9.55 | 9.65 | +7.13 |
| G5@P4 | 34 | +9.25 | 9.73 | +8.31 |
| G5@G5 | 20 | +9.06 | 9.34 | +9.84 |

W2 is hotter than W1 as early soften lifts (1.26 → 1.302). If W3–W4 keep climbing toward raw 1.40, that is confirmatory of the mechanism — still not a reason to retune from the live street.

Home/away: HFA is a ~2-pt additive on the home score. Neutral-site n=3 is too small. Totals bias is not a home/away sign bug.

FBS/FCS excluded (no KEI precision). All rows here are FBS–FBS.

---

## 4. Spread outliers — decompose, do not retune

KEI spread = model + early bias guard (W0–2, cap 1.2). Guard is a small favorite-side nudge. It does **not** create these 15–18 pt gaps.

Two families. None of the six is a leftover `NAME_TO_CODE` hydrate.

### Family A — identity disagreement vs market (favorite flips)

The model’s 2025 SP+ / compose says team X is clearly better. The market prices the other side (or a pick’em).

#### UNLV @ UNT (KEI resid −18.61, flip)

| | UNT (home) | UNLV (away) |
|---|---|---|
| Compose O/D | **1.50 / 1.12** | 1.26 / 1.04 |
| SP+ / off_eff | **13.8 / 83.8** | 4.2 / 64.2 |
| QB | portal Tayven Jackson 1.209 | portal Jackson Arnold 1.121 |
| Model / KEI / mkt | UNT −14.4 / −15.6 | market **UNLV −3** (home +3) |

UNT was a P0 mapping team; after repair it carries real AAC power. The flip vs the broken pack is a **revealed** disagreement, not leftover null hydrate. Primary driver: UNT 2025 offense carry (off_eff 84). Market has not bought 2026 UNT as a 2-score home favorite over UNLV.

Totals: 77.9 vs 57.5 (**+20.4**), inflation +21. Same matchup term.

#### RUT @ BC (KEI resid +16.49, flip)

| | BC (home) | RUT (away) |
|---|---|---|
| Compose O/D | 1.07 / 1.00 | **1.35 / 1.12** |
| SP+ | **−8.7** | +1.0 |
| QB | open-comp Enzo Arjona 1.084 | portal Dylan Lonergan 1.216 |
| Model / KEI / mkt | BC **+12.5 / +13.5** | market **BC −3** |

RUT/BC never had a mapping bug. Model scores RUT 37.9 – BC 25.4. Market has BC as a short home favorite. This is 2025-efficiency + QB-class vs a street that still likes BC at home.

#### USF @ ARMY (KEI resid +16.35, flip)

| | ARMY | USF |
|---|---|---|
| off_eff | **44.9** | **72.5** |
| SP+ | 0.7 | 11.6 |
| Model / KEI / mkt | ARMY **+12.4 / +13.4** | market **ARMY −3** |
| Totals | 67.8 vs **46.5** (+21.3) | |

Service-academy / option game. Street prices a low total and Army as home favorite. Model treats USF’s 2025 explosive offense as fully portable onto Army’s identity and still lets Army score 27.7. Label: **option/service misspec**, not a 1-game bug.

#### SDSU @ UCLA (KEI resid +14.90, flip)

| | UCLA (home, new HC) | SDSU |
|---|---|---|
| SP+ / def_eff | **−8.7 / 41.9** | **+6.7 / 64.2** |
| Roster strength | **65.1** | 55.4 |
| Model / KEI / mkt | UCLA **+1.7 / +2.4** | market **UCLA −12.5** |
| Totals | 50.3 vs 54.5 (**−4.2**, one of two W2 unders) | |

Market is buying Big Ten / brand / Iamaleava. Model is buying SDSU’s 2025 SP+ defense and a weak UCLA carry. Roster/QB actually lean UCLA; efficiency leans SDSU. This is **prior-year efficiency vs current narrative**, and the totals side is *not* Over-drunk — matchup inflation is −1.0.

### Family B — same favorite, model compressed vs cupcake street

#### WKU @ UGA (KEI resid +15.27, no flip)

Model UGA −23.0 / KEI −24.2 vs market **−39.5**. Dog still scores 21.9 because WKU offense_index is 1.22 against UGA’s 1.41 defense (away matchup factor 0.83). Market wants a 3-score more separation. Totals +11.3 (model 66.8 vs 55.5) — favorite scores 44.9, street’s 55.5 total + 39.5 spread implies a much more lopsided script.

#### LT @ LSU (KEI resid +15.01, no flip)

Model LSU −19.3 / KEI −20.5 vs market **−35.5**. **Totals almost right (+0.93).** LSU open-comp QB (Leavitt) + modest off_eff 47.2 compress LSU’s scoring (37.9) while LSU defense (1.40) already sits the dog at 18.6. This is almost a pure **margin/separation** miss, useful as a control: the totals term can be fine while the spread is 15 pts off.

### What these six are *not*

- Not a shared coefficient we should chase on n=6.
- Not one feature (UNT is offense-carry; UCLA is brand vs SP+; Army is option; UGA/LSU are cupcake compression).
- Not a reason to cut global `MATCHUP_RESPONSE` — that would move Family B the “right” way and Family A / totals the wrong way at the same time.

---

## 5. Proposed experiments (do not run into production)

Order is the point. Market numbers stay **eval-only** unless a proposal is explicitly market-aware.

### Experiment 0 — unblock the honest historical path (prerequisite)

**Question:** Can we reconstruct Week-0 real roster + prior-year SP+ for 2023, 2024, 2025 with the same fields live compose reads?

**Already known:** no (`cfb-totals-guard-real-roster-holdout-blocker-20260903`). ESPN current-season roster only; public SP+ archive thin; CFBD keyed/absent; warehouse has no hist rosters.

**Pass:** packaged 2023/24/25 roster snapshots + 2022→23 / 2023→24 / 2024→25 SP+ carries, same schema as 2026.

**Until then:** do not fit a live-roster λ. Do not mix proxy `λ=0.54` onto 2026.

### Experiment 1 — totals, candidate (b), same-path OOS (primary)

Already designed: `docs/CFB_KEI_CALIBRATOR_DESIGN.md`, helpers in `totals_guard_holdout.py`.

```text
kei_total = T0 − (1−λ) * matchup_inflation     # sum only
spread_home unchanged
```

- Fit λ on **2023–24 W0–2** real-roster path only.
- Eval unused **2025 W0–2** (and vs **actual scores**, not just close).
- Report: MAE, RMSE, bias, Over-sign, residual buckets, peer vs cupcake. ATS-vs-close if wanted — **ATS does not unsat PLAY**.
- GREEN bars remain design §4 (abs mean ≤1, MAE not worse >0.3, mean not >+2). If GREEN → **STOP and report**. Do not implement `apply_cfb_kei` from the harness.
- **Forbidden:** fit on 2026 W1/W2; subtract a constant 9–10; cut global `MATCHUP_RESPONSE`; recut this week’s pack.

### Experiment 2 — totals, candidate (a) level offset (fallback only)

`kei_total = model_total + c`, `c` fit 2023–24 W0–2, eval 2025.

Proxy path already GREENS (a) because proxy identity bias is ~0 — that is **not** evidence (a) will work on live identity. If (b) is the mechanism, (a) will over-correct peer games and under-correct UTSA@TXST-style both-score games. Measure that split. Do not ship (a) because it is simpler.

### Experiment 3 — confirmatory week path on frozen 2026 (measure only)

Re-run this diagnostic on W3/W4 with the same frozen math. If mean inflation tracks `matchup_response_for_week` (1.26 → 1.30 → 1.34 → 1.37), the mechanism is confirmed without touching knobs.

Also grade **vs actual scores** once W1/W2 finals lock — street residual ≠ model miss vs reality. A +10 vs books with a +2 vs actuals is a different product decision than +10 vs both.

### Experiment 4 — spread families, historical slices (not these six)

Do **not** add an UNT or Army dummy.

Proposed OOS slices on whatever reconstructable path we have (proxy first, real-roster when unblocked):

1. G5@P4 cupcakes (`|spread|≥17`): favorite-compression vs close **and** vs actual margin (UGA/LSU family).
2. Service academies (ARMY/NAVY/AFA) as a **pre-registered** group: totals and spread, all years, not 2026 Army.
3. Prior-year SP+ vs market on brand programs with negative carry (UCLA family).
4. Open-competition QB vs incumbent on the favorite.

Metrics: MAE, RMSE, bias, favorite-flip rate, residual buckets. Fit nothing on 2026 flips.

A global response cut is **not** an experiment here. It couples totals Family-A inflation to spread Family-B compression and was already used once on the proxy path.

### Experiment 5 — double-count audit (cheap, already mostly done)

Compose blends OL/skill/front-seven **and** applies game-level unit boost/dampen. Net W2 effect of those game-level terms is **−0.9 / +1.1**. Not the +10. Optional: rebuild one season with game-level unit terms forced to 1.0 and compare hist close/actuals. Only worth it after Experiment 0.

---

## 6. What we will not do from this report

- Flip `CFB_EDGE_BOARD_PUBLIC_ENABLED`
- Unsat totals or spread PLAY
- Edit `priors.py` / `team_projection.py` / `apply_cfb_kei`
- Haircut this week’s KEI pack
- Subtract ~10 from published totals
- Fit λ or an offset on W2 street
- Tune to UNLV/UNT, RUT/BC, USF/ARMY, WKU/UGA, LT/LSU, SDSU/UCLA
- Mix proxy-holdout λ onto live roster
- Invent P0 season-win totals or KEI

Public CFB stays dark until Validation signs a later, unused, same-path result — not this 47-game slate.

---

## File index

| Path | Role |
|---|---|
| `scripts/cfb/cfb_model_total_diagnostic.py` | Frozen-path reproject + term CF + slices (this pass) |
| `data/ops/cfb-model-diagnostic-20260911.json` | Numbers behind this note |
| `docs/CFB_TOTALS_HOT_AUDIT.md` | W1 read-only audit (same mechanism) |
| `docs/CFB_KEI_CALIBRATOR_DESIGN.md` | Versioned totals-guard design; not implemented |
| `data/ops/cfb-totals-guard-holdout-20260903.md` | Proxy 2023–25 unused holdout |
| `data/ops/cfb-totals-guard-real-roster-holdout-blocker-20260903.md` | STOP: no real-roster OOS yet |
| `data/ops/cfb-historical-calibration-20260805.md` | Why PPG=25.9 and response=1.40 exist |
| `apps/web/lib/cfb-edge-board-public.ts` | Kill switch stays false |
