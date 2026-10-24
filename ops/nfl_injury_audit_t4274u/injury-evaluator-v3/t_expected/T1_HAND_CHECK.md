# T-1 hand check — spread close-vs-outcome sign (filed BEFORE any v3 run)

**Acceptance:** IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt `54bc78ec` T-1  
**Ruling:** IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v1.txt `a0501d57` E-3  
**This file is the independent answer. The scorer does not write it.**

## Fixture (3 games, identical)

| field | value |
|---|---|
| close spread (home) | −3.0 |
| base spread (home) | −3.0 |
| adj spread (home) | −4.5 |
| actual spread (home) | −4.5  (home won by 4.5; covers −3) |

Home-spread convention: more negative = more home favorite.

## What “edge” means

`edge = spread_arm − close`.  
`edge > 0` ⇒ arm’s home line is *above* the close ⇒ arm is less home-favorite than the close ⇒ arm picks **AWAY**.  
`edge < 0` ⇒ arm picks **HOME**.  
`edge = 0` ⇒ no pick vs close.

Here: base edge = 0 (no pick). adj edge = −4.5 − (−3.0) = **−1.5** (HOME pick). Adj is 1.5 points more home than the close.

## v1 formula (scorer a8ec13a7) — hand evaluation

v1: `CLV = (close − actual_spread) × sign(edge)`  
v1 ATS win if `(edge>0 and home_covered) or (edge<0 and not home_covered)`.

close − actual = −3 − (−4.5) = **+1.5** (home covered).  
adj sign(edge) = −1.  
v1 CLV_adj = 1.5 × (−1) = **−1.5**.  
v1 ATS_adj = edge<0 and home_covered → scored as a **loss**.

The arm that moved toward the covering home side is scored as a loss. **Sign is inverted.** E-3 confirmed.

## Registered rule (T-1)

> CLV_pts(arm) = signed points the arm’s pick beats the close.

This is an **outcome-vs-close** number, not a price-vs-close CLV. Label in all outputs: **close vs outcome** (not certified CLV).

Corrected:

```
picked_home = (spread_arm < close)
picked_away = (spread_arm > close)
home_covered = (actual_spread < close)
cvo_pts = 0                     if no pick
         (close − actual)       if picked home     # + when home covered
         (actual − close)       if picked away     # + when home did not cover
         ≡ sign(close − spread_arm) × (close − actual_spread)
ATS = 1 iff pick matches cover; undefined if no pick
```

Hand values on this fixture:

- base: no pick → cvo_pts = **0**, ATS undefined  
- adj: HOME pick, home covered → cvo_pts = +1.5, ATS = 1  
- **delta (adj − base) = +1.5 exactly** on each of the 3 games (mean +1.5)

## Mirrored fixture

Same close −3.0, base −3.0, actual −4.5; adj = **−1.5** (1.5 toward away).  
adj picks AWAY; home covered → cvo_pts = −4.5 − (−3.0) = **−1.5**.  
**delta = −1.5 exactly.**

## Implied-prob close-vs-outcome (N-2)

```
p_arm = Φ(pred_margin / σ_margin)     # T-5; no √2
p_close = Φ(−close / σ_margin)
cvo_prob = 0 if p_arm == p_close
         (y_home − p_close) × sign(p_arm − p_close)
```

On the primary fixture home won (y=1) and p_adj > p_close, so cvo_prob_adj > 0.  
**Delta sign matches points sign** (+ on primary, − on mirror).

## Erratum (E-3)

The frozen `score_rows` identity that treats `edge>0 & home-covered` as an ATS win is inverted relative to the home-spread convention. v3 uses the corrected formulas above. The metric is labeled **close vs outcome**, not certified CLV.
