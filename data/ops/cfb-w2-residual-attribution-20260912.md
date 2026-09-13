# W2 residual attribution — diagnosis only (2026-09-12)

**Incident:** ESPN-vintage remint is internally consistent. W2 FBS–FBS vs frozen DraftKings snapshot: **mean total residual +9.98**, **10/47 favorite flips**.

**This pass:** explain the residuals. **No coefficient changes. No haircut. No market calibration. No “subtract 10.”** Public CFB Edge Board remains **OFF**. #532 remains **DO NOT MERGE**.

Machine ledger: `data/ops/cfb-w2-residual-attribution-20260912.json`  
Builder: `scripts/cfb/cfb_w2_residual_attribution.py`

---

## Verdict first

| Question | Answer |
|---|---|
| Is +9.98 a comparison-layer artifact? | **No.** Sign convention, home/away, timestamps, join, duplicates, neutrals, and `kei_total ≡ model_total` all check out. |
| Is it `Model = Market + ~10`? | **No.** Mean gap is ~+10, but OLS `model ~ market` is **slope 0.857, intercept +17.58, r² 0.30**. Only 40% of gaps sit within ±3 of the mean. |
| Is it a steep slope/calibration error on the market axis? | **Mostly no.** Market-total buckets sit +9.4 / +9.5 / +11.6. The slope is a weak secondary. |
| Where does the heat come from? | **`(off_idx / opp_def_idx)^1.302` (week-2 matchup response).** Neutralizing that ratio to 1.0 drops mean gap from **+10.10 → +1.14**. |
| Is `LEAGUE_TEAM_PPG = 25.9` too high? | **No.** `2 × 25.9 = 51.8` vs mean market **53.07**. Baseline is slightly *low*. The model over-scores because matchup ratios lift both sides when O/D are asymmetric. |
| Begin calibration on this 47-game sample? | **FAIL.** Mechanism is identified. Fitting n=47 (or subtracting 10) would hide it. |

---

## 0. Comparison-layer proof (do this before blaming the model)

Frozen market: `data/ops/cfb-w2-espn-scoreboard-odds-20260911.json`  
Source: ESPN scoreboard **DraftKings** provider. Snapshot label `as_of_et: 2026-09-11 13:00 ET`.  
Join: **47/47** FBS–FBS scored rows. **0** unjoined. **0** duplicate pairs. **0** W2 neutrals in this pack.

Identity:

- `kei_total ≡ model_total` on all 47 (zero mismatches).
- Reproject via `project_game` vs packed `model_total`: max |Δ| **0.30**, mean **0.13** (rounding / compose-detail drift, not a second totals model).

Sign convention (home-relative, negative = home favorite):

| Game | Market details | `spread_home` | Model `spread_home` | Consistent? |
|---|---|---|---|---|
| RUT @ BC | `BC -3` | −3.0 | +12.46 | Yes. Book: home favorite. Model: visitor favorite. |
| UNLV @ UNT | `UNLV -3` | +3.0 | −14.45 | Yes. Book: visitor favorite. Model: home favorite. |

Home/away orientation follows ESPN `away @ home` labels. Team mapping uses the same official-code resolver as the pack (no FAU2/OLE/ULL collisions on this slate).

**+9.98 is a model-vs-market number, not a join bug.**

---

## 1. How `model_total` is actually built

`expected_team_points` in `team_projection.py`:

```
pts = 25.9
    * (off_idx / opp_def_idx) ^ MATCHUP_EFFECTIVE
    * ol_skill_boost
    * opp_ol_def_dampen
    * pace_factor
    + HFA (home only, ~0.8–2.8)
    + coaching_adj
```

Then a special-teams nudge of `0.015 * (mean(ST) − 50)` is split across both scores.  
`total = home + away`.  
`spread_home = away − home`.

Week-2 `MATCHUP_EFFECTIVE = 1.40 × 0.93 = 1.302`.

**Named components that are NOT in the score path** (they exist on the team object or in other modules, but they do not move `model_total`):

| Component | In score path? |
|---|---|
| Offensive efficiency | Yes, via `off_idx` (compose `WEIGHT_OFF_EFF` 0.34 + `EFF_OFF_INDEX_BLEND` 0.12) |
| Defensive efficiency | Yes, via `def_idx` |
| Pace / expected possessions | Partial. `pace_factor` only; **no explicit possession count** |
| Explosiveness | Tiny. `(expl − 50) / 400` on pace only |
| Finishing drives / scoring conversion | **No** |
| Field position | **No** |
| Special teams | Yes, ~1.5% nudge |
| Opponent interaction | Yes — the matchup ratio, **on top of compose already mixing O/D** |
| Home field | Yes, additive |
| Roster / QB | Yes, inside `off_idx` / `def_idx` |
| Weather | **No** |
| Baseline | Yes, `LEAGUE_TEAM_PPG = 25.9` |
| `success_off` / `success_def` | **No** (carried, unused here) |
| `margin_calibration.apply_calibrated_scores` | **Not on KEI path.** `used_in_spread=false`. Research Bernoulli only. |

KEI `kei_total = model_total` by construction (`cfb_kei.py`). There is no totals haircut.

---

## 2. Total residual attribution

Fleet (packed `model_total − market_total`, n=47):

| Stat | Value |
|---|---|
| Mean residual | **+9.976** |
| Median | +9.25 |
| MAE | 10.265 |
| RMSE | 11.564 |
| Overs / Unders | **45 / 2** |
| Mean model total | 63.05 |
| Mean market total | 53.07 |
| Gap SD | 5.85 |
| Share of gaps within ±3 of mean | 40.4% |
| Share within ±5 of mean | 63.8% |

The two Unders are **SDSU@UCLA (−4.17)** and **APP@ECU (−2.63)**. Highest residual: **USF@ARMY +21.02** (model 67.52 vs market 46.5).

OLS `model_total ~ market_total`:

```
model = 0.857 × market + 17.58     r² = 0.30
implied gap at market 50 / 55 / 60:  +10.6 / +9.8 / +9.2
```

That is a **level shift with a weak downward slope**, not a clean intercept-only error and not a wild slope error. A constant −10 haircut would flatter this week’s MAE and still be wrong on the tails (projected ≥62 residual **+13.11**; projected <55 residual **+3.88**).

### Component contribution to the +9.98 (counterfactual, same 47 games)

Reproject every game with one term neutralized. Δ = counterfactual mean gap − actual mean gap (− means “this term was adding heat”).

| Neutralize | Mean gap vs market | Δ vs actual (+10.10) |
|---|---|---|
| Actual (reproject) | +10.10 | — |
| Matchup ratio → 1.0 | **+1.14** | **−8.96** |
| Units boost/dampen → 1.0 | +10.27 | +0.17 (units were *cooling*) |
| Pace → 1.0 | +9.91 | −0.19 |
| No HFA / coaching / ST | +7.52 | −2.58 |
| Both sides = 25.9 (total 51.8) | −1.27 | −11.38 |

**~90% of the mean residual is the matchup-response term.**  
HFA/coaching/ST explain ~2.6 points of the remaining level (every home team gets +HFA; both sides get coaching/ST).  
Pace is almost neutral. Units are slightly *deflating* totals.  
The 25.9 baseline, used alone, would *undershoot* the street.

### Segments (packed residual)

| Slice | n | Mean | Median | MAE | RMSE |
|---|---|---|---|---|---|
| All | 47 | +9.98 | +9.25 | 10.27 | 11.56 |
| Market total <50 | 12 | +11.55 | +12.34 | 11.55 | 12.46 |
| Market 50–55 | 17 | +9.38 | +7.85 | 9.87 | 11.11 |
| Market ≥55 | 18 | +9.49 | +8.83 | 9.78 | 11.36 |
| Projected total <55 | 5 | +3.88 | +4.70 | 6.60 | 7.55 |
| Projected 55–62 | 14 | +5.89 | +6.74 | 5.89 | 6.50 |
| Projected ≥62 | 28 | **+13.11** | +13.33 | 13.11 | 13.90 |
| Fast pace | 5 | **+18.10** | +18.90 | 18.10 | 18.41 |
| Mid pace | 32 | +9.76 | +9.00 | 9.92 | 11.09 |
| Slow pace | 10 | +6.62 | +6.90 | 7.46 | 8.09 |
| High mean off_eff | 16 | **+15.19** | +15.33 | 15.19 | 15.85 |
| Mid | 18 | +7.44 | +7.82 | 7.73 | 8.49 |
| Low | 13 | +7.08 | +7.14 | 7.72 | 8.63 |
| P4/P4 | 18 | +10.50 | +9.37 | 10.50 | 11.96 |
| G5/G5 | 15 | +10.60 | +9.48 | 10.95 | 12.34 |
| Cross | 14 | +8.64 | +8.83 | 9.24 | 10.11 |
| Home favorite (mkt) | 34 | +10.45 | +10.62 | 10.85 | 12.08 |
| Away favorite (mkt) | 13 | +8.74 | +7.67 | 8.74 | 10.10 |

Pattern: residual grows with **projected total**, **offensive efficiency**, and **pace** — exactly where `(off/def)^1.302` bites. Residual is **stable across market-total buckets**. That is intercept-like on the *market* axis and slope-like on the *model* axis.

### Per-game ledger

Each of the 47 games in the JSON has market / model / KEI lines, indexes, efficiencies, pace, explosiveness, roster, QB, matchup ratio, units, HFA, coaching, ST nudge, reconstructed points, and counterfactual totals **and spreads**.

---

## 3. Favorite-flip attribution (10/47)

KEI favorite ≠ market favorite. None of these is a hydrate/null-power artifact. All ten have real `off_idx` / `def_idx` on both sides.

The important new measurement: **set matchup ratio → 1.0 and watch the spread.** For most large flips the model collapses toward a 1–3 point home favorite — i.e. the flip *is* the matchup term, not a second hidden bug.

| Game | KEI / model | Market | Residual | Matchup→1 spread | Classification |
|---|---|---|---|---|---|
| UNLV@UNT | −15.65 / −14.45 | +3.0 | −18.65 | **−2.05** | **1 — data-revealed, then matchup-stretched.** UNT `off_idx` 1.50 / off_eff **84.0** (was unmapped at W0). Without matchup the model is UNT −2 vs book UNLV −3. The giant number is `(1.44)^1.302`. |
| RUT@BC | +13.46 / +12.46 | −3.0 | +16.46 | **−1.40** | **2 — matchup-stretched; see §4.** Without matchup: BC −1.4 vs book BC −3. |
| USF@ARMY | +13.30 / +12.30 | −3.0 | +16.30 | **−1.28** | **2 — matchup on the spread; leftover on the total.** Spread CF agrees with the book. Total still 55.2 vs 46.5 after matchup (Army option / low-possession market the model does not have). |
| SDSU@UCLA | +2.38 / +1.71 | −12.5 | +14.88 | **−0.04** | **1 — 2025-final vs 2026 book, not matchup.** ESPN SP+: SDSU **+6.7** vs UCLA **−8.7**. Model is a pick’em. Book is UCLA −12.5. |
| ULM@UAB | +4.49 / +4.10 | −10.0 | +14.49 | **−1.11** | **2 — matchup creates the flip; compose is also suspicious.** UAB `def_idx` **0.874**. ULM `off_eff` **26.38** still composes to `off_idx` 1.10 (roster/QB/units washing a terrible offense). Book UAB −10 remains far from CF −1.1. |
| CAL@SYR | +9.00 / +8.00 | −3.5 | +12.50 | **−1.52** | **2 — matchup-stretched.** Without matchup: SYR −1.5 vs book SYR −3.5. |
| NAVY@FAU | −4.48 / −3.89 | +4.5 | −8.98 | **−2.67** | **1 — not mostly matchup.** FAU still home favorite without the ratio. Book has Navy −4.5 (option style the model treats as generic efficiency). |
| ARI@BYU | +1.33 / +0.51 | −7.5 | +8.83 | **−2.10** | **1 — book buying BYU.** Matchup moves the model from BYU −2.1 to a pick’em. Leftover ~5.4 is 2026 information / brand. |
| MSST@MINN | −3.85 / −3.17 | +1.5 | −5.35 | **−1.46** | **1 — small.** Matchup explains ~1.7 of ~4.7. Ordinary home lean. |
| OSU@TEX | +3.62 / +3.11 | −1.5 | +5.12 | **−2.88** | **2 — matchup-stretched chalk.** Without matchup: TEX −2.9 vs book TEX −1.5. OSU `away_matchup` 1.1605 vs TEX ~1.00, then ^1.302. |

**Matchup-stretched (would nearly agree with the book if the ratio were 1):** RUT@BC, USF@ARMY (spread), CAL@SYR, OSU@TEX.

**Legitimate model-vs-market / 2026 information:** SDSU@UCLA, NAVY@FAU, ARI@BYU, MSST@MINN.

**Data-revealed then stretched:** UNLV@UNT.

**Suspicious compose:** ULM@UAB (`off_eff` 26 → `off_idx` 1.10 into `def_idx` 0.87).

---

## 4. RUT@BC forensic

**Join is correct.** ESPN: “Rutgers Scarlet Knights @ Boston College Eagles”, DK `BC -3` / 53.5. Pack pair `RUT@BC`. Neutral: false.

ESPN 2025-final SP+: **RUT +1.0 (rank 72, 5–7)** vs **BC −8.5 (rank 97, 2–10)**.

| | RUT (away) | BC (home) |
|---|---|---|
| SP+ 2025 ESPN | +1.0 | −8.5 |
| off_eff / def_eff | 59.49 / 41.10 | 41.76 / 36.06 |
| explosiveness | 58.96 | 39.49 |
| off_idx / def_idx | **1.348 / 1.122** | 1.068 / 1.004 |
| matchup ratio / ^1.302 | **1.342 / 1.464** | 0.952 / 0.938 |
| pace factor (team / diag) | 1.015 / 0.988 | 0.961 / 0.988 |
| roster | 66.9 | 61.1 |
| QB | portal, idx **1.216** | open_competition, idx 1.084 |
| HFA | 0 | +2.00 (1.7 + 0.3 night) |
| coaching net | +0.13 | +0.13 |
| reconstructed pts | 37.97 | 25.81 |

Packed: model spread **+12.46**, KEI **+13.46**, total **63.48** (residual vs 53.5 = **+9.98**, fleet-mean).  
Reproject: +12.16 / 63.78.

Counterfactuals on this game:

| | Total | Spread (home-signed) |
|---|---|---|
| Actual | 63.78 | **+12.16** (RUT −12.2) |
| Matchup → 1 | **53.32** | **−1.40** (BC −1.4) |
| Units → 1 | 64.03 | +11.53 |
| Pace → 1 | 64.51 | +12.32 |
| No HFA/coach/ST | 61.31 | +14.16 |
| Market | 53.5 | −3.0 (BC −3) |

**The total gap vs 53.5 is almost entirely matchup inflation** (53.32 vs 53.5).  
**The favorite flip is the same term.** Without the ratio, the model is BC −1.4 — one and a half points from the book.

Layered read of the spread (not a fit, just arithmetic):

1. Identity (ratio = 1) + HFA/units/coach → **BC −1.4** (book is BC −3).
2. Linear ratio (`^1.0`, not in the ledger; hand check) would keep the composed quality gap and land near **RUT −8 to −9**.
3. Week-2 exponent `^1.302` stretches that to **RUT −12.2**.

So the ~19.5-point disagreement is:

- ~10 points from scoring the composed index gap through the matchup ratio at all (RUT 1.35 / BC 1.07, RUT portal QB 1.216 vs BC open 1.084, 2025 SP+ +1.0 vs −8.5),
- ~3–4 points from raising that ratio to 1.302,
- **not** a join bug, not live-2026 SP+, not a missing weather/possessions term.

Whether the *book* is right (BC −3) is a 2026 information question. The *machinery* is doing what it is written to do, and the drunk term is the same one heating the totals.

---

## 5. Suspected root causes (ranked by evidence)

1. **Week-2 matchup response (1.40 × 0.93 = 1.302) applied to already-composed indexes.**  
   Evidence: neutralizing the ratio removes **8.96** of **10.10** mean total gap; RUT@BC total and spread both fall on the market; high-off_eff and high-projected buckets carry +13 to +15; four of the ten favorite flips disappear.  
   This is the “Over-drunk identity”: the identity is honest; the drunk term is `(O/D)^1.302`.

2. **Double use of efficiency.** Efficiency is inside `off_idx` (`WEIGHT_OFF_EFF` 0.34 + `EFF_OFF_INDEX_BLEND` 0.12) and again in the game-level ratio. Units were already softened for this reason; matchup was not.

3. **No explicit possession / drive / finishing / field-position model.**  
   Totals are `2 × 25.9 × f(indexes) × pace_factor`. Fleet pace is almost 1.00 (neutralizing it moves the mean gap by 0.19). The model cannot be “wrong about possessions” in general because it does not compute them. **Exception:** USF@ARMY leftover +8.7 after matchup, market 46.5 — that is a style/tempo game the pace_factor does not capture.

4. **Compose washing extreme efficiencies.** ULM `off_eff` 26.38 → `off_idx` 1.10. Roster/QB/unit weights can overwrite a terrible offense before the matchup term ever fires.

5. **Additive HFA + coaching + ST on both sides** (~+2.6 to the mean total). Real, small, not the story.

6. **`LEAGUE_TEAM_PPG = 25.9` is not the culprit.** Alone it undershoots the street.

7. **Stale 2025-final efficiency vs 2026 week-2 market** is a *subset* of the spread story (SDSU@UCLA, ARI@BYU, NAVY@FAU), not the +10 totals story. Totals residual is stable across P4/P4 and G5/G5.

8. **Comparison layer / KEI identity / vintage contamination** — ruled out this pass.

What this is **not**: live-2026 SP+ leakage. Efficiency rows in this remint are ESPN 2025-final. The +10 was already in #536 (mean residual +9.94). Vintage repair did not create it.

---

## 6. Proposed remediation experiments (do not run as a ship decision)

All of these are **experiments**, not this-PR patches. Holdout must be **not** this 47-game DK snapshot (W1 scored, W0-close replay, or a later week).

| ID | Experiment | What it tests | Success look |
|---|---|---|---|
| E1 | Replay W2 with `MATCHUP_RESPONSE = 1.0` (keep week factor). | Cause 1. | Mean total residual → ~+1 to +3; RUT@BC / CAL@SYR / OSU@TEX flips should collapse toward the book. |
| E2 | Replay with `MATCHUP_RESPONSE = 1.15` and `1.25` (grid, not a fit). | Dose-response / exponent vs ratio. | Residual vs response should be roughly linear if cause 1 is right. |
| E3 | Replay with matchup on **SP+ only** (or raw off/def), not composed `off_idx`. | Cause 2 (double count) and cause 4 (compose wash). | Totals cool; ULM@UAB should move if the 26→1.10 wash is real. |
| E4 | Rebuild totals as `possessions × pts_per_poss` from tempo + finishing, leave spread on current path. | Cause 3. | Should move USF@ARMY / option games first; fleet intercept should not magically vanish if cause 1 is right. |
| E5 | Drop HFA/coach/ST from *totals only* (keep on spread). | Cause 5. | Mean residual −2.6; if leftover is still ~+7, cause 1 remains. |
| E6 | **Do not** subtract 10. If someone needs a strawman, apply −10 and show it fails on low-projected / SDSU@UCLA / APP@ECU / market≥55 buckets. | Proves intercept-only haircut is the wrong shape. | MAE looks better, segment residuals do not. |

**Do not** optimize any of E1–E5 against these 47 games. Use them to confirm mechanism, then design a calibration on a reserved set.

---

## 7. PASS / FAIL — beginning calibration

**FAIL.**

Reasons:

- Mechanism is identified. Calibration before a holdout experiment would fit the symptom.
- n=47, one snapshot, one week, one book. That is a diagnosis sample, not a fit sample.
- Shape is not `Model = Market + 10`. A constant offset would hide high-projected / high-off_eff overheat and would punish the two honest Unders.
- Favorite flips are mixed (matchup-stretched vs 2026-information vs compose-wash). Do not regularize them into the book.
- Kill switch stays **OFF**. This report does not authorize public totals or a totals guard change.

**PASS** would require: E1/E2 (or E3) run on a **held-out** week, residual shape documented, and a written proposal that changes `MATCHUP_RESPONSE` or the score identity — not a silent −10.

---

## 8. What we are not doing

- Not subtracting 10 from every total.
- Not retuning coefficients in this PR.
- Not chasing #536.
- Not turning the board on.
- Not merging #532.

Source-vintage incident remains **ROOT CAUSE IDENTIFIED / REMEDIATED**. Provenance and fail-closed tests stay. This document opens the **model residual attribution** phase.
