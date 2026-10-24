# T-1 hand check — spread close-vs-outcome sign + B-1 no-pick ATS

**Acceptance:** IMV_SPEC_NFL_INJURY_PRE_HOLDOUT_ACCEPTANCE_v1.txt `54bc78ec` T-1  
**Ruling (wins):** IMV_RULING_NFL_INJURY_EVALUATOR_READINESS_v2.txt `1a090e3b` B-1 / E-3  
**Prior ruling:** `a0501d57` E-3 (sign closed; ATS no-pick was the remaining defect)  
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
`edge > 0` ⇒ arm picks **AWAY**.  
`edge < 0` ⇒ arm picks **HOME**.  
`edge = 0` ⇒ no pick vs close.

Here: base edge = 0 (no pick). adj edge = −1.5 (HOME pick).

## Registered rule (T-1 + B-1)

```
picked_home = (spread_arm < close)
picked_away = (spread_arm > close)
cvo_pts = 0                     if no pick
         sign(close − spread_arm) × (close − actual_spread)   otherwise
ATS = None                     if no pick (model == close)
    1 iff pick matches cover    otherwise
    never score a no-pick as a loss (0)
```

Same no-pick rule for total/ML ATS when `p == 0.5`.

Hand values on this fixture:

- base: no pick → cvo_pts = **0**, ATS = **None** (not 0)
- adj: HOME pick, home covered → cvo_pts = +1.5, ATS = 1
- **delta (adj − base) = +1.5** on each of the 3 games
- ATS delta uses only both-defined rows (E-7 / 54bc78ec T-7): base ATS is undefined, so spread_ats_delta is undefined on this fixture, not a 0−1 loss.

## Mirrored fixture

adj = **−1.5** (away). cvo_pts = **−1.5**. delta = **−1.5**.

## p == 0.5 fixture (B-1)

4 games: `pred_margin = 0` so `p_home = 0.5`; `pred_total = close_total` so `p_over = 0.5`.  
ML ATS and total ATS must be **None**, not a loss.

## T-4 log-loss erratum (1a090e3b)

`-(ln(0.8)+ln(0.4)+ln(0.7))/3 = 0.49870307570903244`.  
54bc78ec printed 0.498434; that printed value is wrong. Registered answer is **0.498703**.

## T-9 leak rule (d18ebf22 / 501e8a99; prior 88da5f42)

Parse every timestamp to UTC. Enforce:

```
source_ts <= as_of_ts < kickoff_utc
```

Fail closed on missing or unparseable. **P-4:** a naive / zoneless timestamp is STOP (do not interpret as ET). One fixture per violation: source after as_of; as_of = kickoff; as_of after kickoff; unparseable; missing; naive_zoneless.

**P-2 / C-2 / D-5:** exclude exactly these 11 C-5 `complete=false` `game_id`s, identically in both arms: `2013_1_CIN_CHI`, `2013_1_NYG_DAL`, `2014_15_SF_SEA`, `2015_1_NO_ARI`, `2017_1_IND_LA`, `2020_1_GB_MIN`, `2020_6_KC_BUF`, `2022_2_IND_JAX`, `2022_7_CHI_NE`, `2022_12_BAL_JAX`, `2023_5_HOU_ATL`. Counts 11 total; 3 in 2022; 1 in 2023. Require null `delta_margin` / `delta_total` and null `source_ts` / `as_of_ts` / `kickoff_utc` / `source_ts_home` / `source_ts_away` on each. Complete+null timestamp → STOP. Incomplete+timestamp or non-null delta → STOP. Unexpected incomplete id → STOP. **Pinned id present but `complete=true` → STOP on set mismatch (D-5).**

**Holdout incomplete-row rule (pre-declared):** count and pin `game_id`s from the holdout export **before** any outcome or close join. Same null-delta and null per-side timestamp contract. Do not pre-declare a 2024/25 count.

**P-1/W-2:** pin on-disk export `a38a55bb`. `46d2a565` is the blob hash only.

## Erratum (E-3 sign)

v1 scored the covering home-side move as a loss. v3/v4 use the formulas above. Metric label: **close vs outcome**.
