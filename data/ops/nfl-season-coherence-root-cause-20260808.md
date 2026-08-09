# NFL Season Coherence — Root Cause (Phase 1)

Date: 2026-08-08  
Engine before: `nfl-season-engine-v1.15-true-pr-harden` (published board still on v1.12)  
Engine after: `nfl-season-engine-v1.16-season-coherence`

## Confirmed failure (live board)

Fantasy / preseason-sim player projections showed **32/32 QB1s with `passYardsTotal` ≥ 4000**
(range ~4011–4575, mean ~4269) on bundle `nfl-preseason-sim-2026-20260808T011817Z`.

2025 reality: **6** QBs ≥ 4000. Matching league totals while flattening every QB1 above 4k
is a **coherence failure**, not a ranking cosmetic.

## Where totals are produced

| Path | Producer | Field |
|------|----------|-------|
| Season-engine research → web CSV | `simulate_full_season` → `pass_yards_mean` published as `pass_yards_total` | Path C (live desk fallback) |
| Fantasy weekly baselines | `SUM(pass_yards_mean)` + QB starter lock | Path A (API when populated) |
| Game boxes | per-game only; no season total | Path B |

The broken board was Path C (season-engine means), with Path A able to reproduce the same
shape via unconstrained weekly means × 17.

## Why every QB1 collapsed into ~4.0–4.6k

Closed-form identity of the pre-fix engine:

```
attempts/game ≈ LEAGUE_BASE_PLAYS × LEAGUE_BASE_PASS_RATE × QB1_START_RATE
             ≈ 63.5 × 0.58 × 0.955 ≈ 35.2
yards/game   ≈ attempts × DEFAULT_YPA ≈ 35.2 × 7.15 ≈ 251.5
season       ≈ 251.5 × 17 ≈ 4275
```

Mechanisms that kept everyone in that band:

1. **Shared game pace** — `GameScript.pace_plays` was one number for both teams
   (`0.5 × (home.pace + away.pace)`), so attempt volume barely differed by club.
2. **Tiny pass-rate identity** — coaching `pass_rate_bias` clamped to ±0.035 and
   strength bias applied 1:1 → almost no season pass-volume ladder.
3. **Shared DEFAULT_YPA (7.15)** — most QB roles (and finite caps) used the same
   efficiency; demo talent bumps only covered a handful of names.
4. **Finite caps used the same DEFAULT_YPA** — `team_production_caps` compressed
   extremes toward the identical pool, so path noise could not create a real
   left/right tail on the published *mean*.
5. **No season team budget / league pool shape contract** — per-game caps existed,
   but nothing enforced a realistic QB1 *distribution* across 32 clubs.

Summing weekly means is statistically fine (linearity of expectation). The bug was
**identical weekly means**, not the sum operator.

## Fix principle (v1.16)

One machine: **team budgets → usage → production → points bridge → W/L**, with
defense slate + coaching inside volume, and conserved league pools. Not a
shadow fantasy model that invents QB means after the fact.
