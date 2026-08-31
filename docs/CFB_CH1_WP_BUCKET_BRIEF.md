# Chapter 1 Phase 0 — 2019–2025 margin→points by bucket (DISCOVERY ONLY)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after Chapter 0 bucket scorecard  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Do not edit the curve in this PR.**

Chapter 0 tape (locked):

- Mid vs cupcake residuals **opposite-signed** (`same_sign: false`)
- W0 mid mean (KEI − close): **−12.89** (TCU too long)
- W0 cupcake mean: **+9.85** (USC/FSU too short)
- Hawaii: **wrong side** (+15.4 vs close −4.5)
- Canaries: BALL **−42.2** · TCU **≈ −20.39** · HAW **+10.90**

That is why Chapter 1 exists. One historical curve. No `if TCU`.

---

## Laws

Program laws from `docs/CFB_ENTERPRISE_PROGRAM.md`.

Canaries frozen until Phase 1 (a later PR) is gated:

- BALL@OSU KEI −42.2
- UNC@TCU KEI ≈ −20.39
- HAW@STAN KEI +10.90
- Top-7 power order
- USF E[wins] separated from OSU by power, not cloned

---

## What Phase 0 must answer

1. **Function spine** — power off/def → expected scores / margin → WP → KEI spread. File:line each hop.
2. **Where a single SD / logistic lives** (`WIN_PROB_MARGIN_SD`, `SCORE_NOISE_SD`, cupcake saturation). Quote constants.
3. **Historical corpus** — path to 2019–2025 FBS games + closing spreads. Row counts by season.
4. **Bucket counts** using Chapter 0 edges: pick 0–3, short 3–7, mid 7–14, long 14–21, cupcake 21+. Split P4 / G5 / FCS if labels exist.
5. **Current in-sample residual** if you can score the _existing_ curve on 2024–2025 holdout **without writing new fit code**. If you cannot, say so — do not sneak a fit.
6. **Phase 1 allowlist** — named files that _would_ change in the next PR.
7. **Risk** — what would shuffle top-7 if Phase 1 is sloppy.

### Greps

```bash
rg -n "win_prob_from_expected_scores|WIN_PROB_MARGIN_SD|SCORE_NOISE_SD|apply_cfb_kei|expected_margin" \
  services/model-service/src/services/cfb_season_engine scripts/cfb | head -200

rg -n "closing_lines|odds_lake|historical_warehouse|2019" \
  services/model-service scripts/cfb | head -150
```

---

## Phase 1 is NOT this PR

When this audit is gated, a **separate** brief will allow:

- Fit margin→spread / WP by bucket on 2019–2024, hold out 2025 (or walk-forward — audit must recommend which the warehouse supports)
- Re-emit KEI pack + re-sim N=10,000
- Scorecard: TCU residual vs −7.5, Hawaii side, BALL vs −50.5, top-7 flat, USF still un-cloned
- Blocker if TCU stays −20 after an honest fit — do not stretch one SD to fake −8.5

Do not start that work here.

---

## Done (this chapter slice)

- Audit exists with spine, constants, corpus counts, bucket N
- Zero product number changes
- Canaries still the Chapter 0 values
- Operator can gate Phase 1 fit as its own PR

## Fail

- Any diff to `apply_cfb_kei` / `power_sot` / priors in this PR
- Training on the six W0 games only
- Team-name branches
