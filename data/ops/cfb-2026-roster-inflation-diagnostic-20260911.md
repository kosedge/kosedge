# 2026 CFB roster/QB/unit scoring inflation (research diagnostic)

**Date:** 2026-09-11  
**Branch:** `cursor/cfb-roster-inflation-1bf8`  
**After:** #538 STOP (hist inflation did not reproduce; SP+ not primary)  
**Kill switch:** `CFB_EDGE_BOARD_PUBLIC_ENABLED = false` — unchanged  
**Production model:** not modified. No λ. No offset. No clamp. No PLAY.  
**2025:** still sealed. #538 artifacts not edited.

Market numbers on 2026 W1/W2 are **confirmatory measurement**, not a loss to tune.

## Verdict

**Primary mechanistic cause:** QB talent location (2025 attempts formula), no defensive twin

talent_from_qb_stats uses base 42 + attempt/YPA/TD terms. A typical FBS starter (≈250–300 att) prints ~67, not 50. 50 means 'no signal' in hist-cal, not 'league-average starter'. Index = 1+(talent-50)/80 then × incumbent 1.06. Mean live QB index is ~1.20. Offense compose gets 0.24 + blend 0.26; defense gets nothing. That is the +7 to +9.

The +7 to +9 is **not** a recruiting-unit intercept and **not** SP+. Recruiting-channel and unit-headline ablations leave the Over intact (units_50 makes it worse). The live 2025-attempt QB talent formula prints a typical starter near 67, not 50 — hist-cal never had that signal — and there is no defensive twin. `MATCHUP_RESPONSE=1.4` then turns the off>def gap into sum inflation.

## 1. End-to-end path (frozen, unchanged)

```text
recruiting prior (floor often 55, not 50)
  → blend_roster_metrics: returning / portal / experience re-anchored to recruiting
  → roster_strength = 0.32·ret + 0.26·portal_net + 0.26·recruiting + 0.16·exp
  → unit talent = 0.62·recruiting + 0.22·exp + 0.16·returning   # recruiting again
  → QB talent = stats, or sqrt(att/80) blend to recruiting      # recruiting again if thin
  → compose offense: 0.34·SP+ + 0.22·roster + 0.24·QB + 0.10·skill + 0.10·OL
                + QB blend 0.26 + OL/skill blends
  → compose defense: 0.36·SP+ + 0.12·roster + 0.24·F7 + 0.20·sec + 0.08·exp
  → pts = 25.9 · (off/def)^response · unit_off_boost · opp_def_dampen · pace
```

Double-count audit (packaging, not a silent 2026 substitute):

| Channel | Enters again as |
|---|---|
| Recruiting | roster_strength (0.26); unit talent (0.62); unit portal_impact (0.35); returning/portal/exp *baselines*; thin QB talent fallback |
| Returning | roster_strength (0.32); unit talent (0.16); already 60% recruiting-baseline |
| Portal | roster_strength via net; unit portal_impact; already 55% recruiting-baseline |
| Experience | roster_strength (0.16); defense compose (0.08); unit experience; already 45% recruiting-baseline |
| QB | offense compose 0.24 + post-compose blend 0.26; no defensive twin |
| Units | compose weights **and** game `UNIT_OFFENSE_BOOST` / `UNIT_DEFENSE_DAMPEN` |

Defaults that systematically lift scoring: packager recruiting fallback **55** (not 50); `portal_out` default 52 in `build_roster_construction` when a row is missing; QB class `incumbent` multiplier **1.06**.

## 2. FBS live distributions (width, not just the mean)

- n FBS = 136
- recruiting exactly 55 (floor): **65**
- recruiting ≥ 80: 23
- QB classes: `{'open_competition': 24, 'incumbent': 70, 'portal': 37, 'true_freshman': 5}`
- QB index ≥ knee 1.25: **58**; near rail ≥1.37: 11

QB talent by class:

- `incumbent` n=70 mean=67.9406 sd=9.066 p10=55.4 p90=79.219
- `open_competition` n=24 mean=60.3846 sd=6.3375 p10=53.239 p90=69.111
- `portal` n=37 mean=70.257 sd=7.2804 p10=61.806 p90=80.742
- `true_freshman` n=5 mean=54.67 sd=4.2799 p10=51.222 p90=59.518

| Component | mean | sd | p10 | p50 | p90 |
|---|---:|---:|---:|---:|---:|
| recruiting | 66.5515 | 12.6292 | 55.0 | 66.0 | 87.0 |
| returning | 61.0739 | 4.3461 | 55.525 | 60.57 | 67.295 |
| portal_in | 57.9468 | 5.7403 | 50.205 | 57.95 | 65.25 |
| experience | 56.4127 | 4.2244 | 51.64 | 55.99 | 61.815 |
| roster_strength | 61.1581 | 5.6082 | 54.365 | 60.825 | 68.9 |
| qb_talent | 66.7495 | 9.0043 | 54.615 | 67.125 | 78.625 |
| qb_index | 1.1995 | 0.1486 | 0.9517 | 1.2146 | 1.3639 |
| ol | 59.9948 | 6.0416 | 52.635 | 59.95 | 68.12 |
| skill | 59.9355 | 5.9443 | 52.66 | 59.555 | 67.96 |
| front_seven | 60.5649 | 5.9233 | 53.065 | 60.11 | 69.1 |
| secondary | 60.4402 | 6.0743 | 53.235 | 59.945 | 69.65 |
| off_eff | 50.1374 | 15.1694 | 29.0 | 49.97 | 69.98 |
| def_eff | 49.9794 | 15.2739 | 30.845 | 48.42 | 70.34 |
| offense_index | 1.2143 | 0.1893 | 0.9958 | 1.1955 | 1.4732 |
| defense_index | 1.1215 | 0.1579 | 0.9323 | 1.1005 | 1.3818 |

### Centering vs width

- mean offense_index = **1.2143**, sd = 0.1893
- mean defense_index = **1.1215**, sd = 0.1579
- mean QB index = **1.1995** (1.0 is league-average)
- mean OL − F7 = -0.5701; skill − secondary = -0.5047

### Correlations (recruiting is the common factor)

- `recruiting_vs_roster_strength` = 0.9046
- `recruiting_vs_ol` = 0.8659
- `recruiting_vs_skill` = 0.8703
- `recruiting_vs_front_seven` = 0.867
- `recruiting_vs_secondary` = 0.8656
- `recruiting_vs_qb_talent` = 0.381
- `recruiting_vs_offense_index` = 0.7196
- `recruiting_vs_defense_index` = 0.8472
- `offense_index_vs_defense_index` = 0.7235
- `roster_strength_vs_ol` = 0.9421
- `qb_index_vs_offense_index` = 0.6401
- `off_eff_vs_offense_index` = 0.8134

## 3. One-at-a-time ablations (2026 W1/W2 books, confirmatory)

SP+ / HFA / coaching stay live unless the variant name says otherwise. Deltas are vs frozen. Negative resid delta = less Over-drunk.

| Variant | mean T | mean resid | MAE | pred SD | p10 / p50 / p90 | infl | Δ resid | Δ MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| frozen | 61.9579 | 9.1357 | 9.425 | 7.0058 | 53.839 / 61.635 / 71.142 | 8.0763 | 0.0 | 0.0 |
| recruiting_field_50 | 61.483 | 8.6608 | 9.0126 | 7.0412 | 53.479 / 61.025 / 70.731 | 7.6013 | -0.4749 | -0.4124 |
| recruiting_channel_50 | 61.7802 | 8.958 | 9.3398 | 7.5729 | 51.886 / 61.65 / 70.203 | 7.7103 | -0.1777 | -0.0852 |
| returning_50 | 61.618 | 8.7958 | 9.1396 | 7.0331 | 53.567 / 61.39 / 70.865 | 7.7362 | -0.3399 | -0.2854 |
| portal_50 | 61.7299 | 8.9077 | 9.2252 | 7.0016 | 53.618 / 61.395 / 71.083 | 7.8482 | -0.228 | -0.1998 |
| experience_50 | 62.347 | 9.5248 | 9.7517 | 7.0355 | 54.159 / 61.79 / 71.696 | 8.4652 | 0.3891 | 0.3267 |
| roster_strength_50 | 60.7922 | 7.97 | 8.4653 | 7.0788 | 52.752 / 60.49 / 69.927 | 6.9105 | -1.1657 | -0.9597 |
| units_50 | 64.473 | 11.6508 | 11.7203 | 7.4157 | 55.125 / 64.365 / 74.001 | 10.3136 | 2.5151 | 2.2953 |
| units_and_cast_50 | 63.7172 | 10.895 | 11.0074 | 7.4539 | 54.404 / 63.28 / 73.569 | 9.558 | 1.7593 | 1.5824 |
| qb_talent_50 | 54.9242 | 2.102 | 4.5553 | 6.0646 | 47.385 / 54.035 / 63.315 | 1.0423 | -7.0337 | -4.8697 |
| qb_class_unknown | 59.6884 | 6.8662 | 7.3887 | 6.6438 | 52.213 / 59.485 / 68.955 | 5.8071 | -2.2695 | -2.0363 |
| qb_league | 51.8043 | -1.0179 | 3.9966 | 5.6617 | 45.849 / 50.655 / 59.759 | -2.0771 | -10.1536 | -5.4284 |
| game_units_50_indices_live | 61.9262 | 9.104 | 9.3784 | 6.997 | 53.792 / 61.405 / 71.141 | 7.9511 | -0.0317 | -0.0466 |
| qb_and_units_50 | 53.6278 | 0.8056 | 3.8531 | 5.7715 | 46.679 / 53.125 / 61.964 | -0.5313 | -8.3301 | -5.5719 |
| roster_qb_units_league | 52.8936 | 0.0713 | 3.7582 | 5.8029 | 46.313 / 52.345 / 61.147 | -1.2655 | -9.0644 | -5.6668 |
| off_layers_league_def_live | 44.0188 | -8.8034 | 9.0926 | 5.7062 | 37.118 / 43.375 / 51.338 | -6.274 | -17.9391 | -0.3324 |
| def_layers_league_off_live | 73.6 | 20.7778 | 20.7778 | 8.8311 | 62.381 / 73.34 / 87.065 | 15.7252 | 11.6421 | 11.3528 |

### Frozen calibration by predicted-total bucket

| Bucket | n | mean resid | MAE |
|---|---:|---:|---:|
| 48-52 | 6 | 0.6167 | 2.4467 |
| 52-56 | 12 | 5.3725 | 6.0325 |
| 56-60 | 20 | 4.8905 | 5.2475 |
| 60-68 | 34 | 10.63 | 10.63 |
| >=68 | 18 | 16.3783 | 16.3783 |

## 4. Minimum component / interaction that reproduces +7 to +9

Minimum necessary component: **QB talent** (qb_talent_50 resid=2.102). That single field takes frozen +9.14 → ~+2. Full QB neutralize (qb_league resid=-1.0179) crosses through zero. Class/cast are the leftover ~3 pts. Recruiting channel and units do **not** reproduce or remove the +7 to +9.

## 5. Ranked suspected causes

1. **QB talent location (2025 attempts formula), no defensive twin** — talent_from_qb_stats uses base 42 + attempt/YPA/TD terms. A typical FBS starter (≈250–300 att) prints ~67, not 50. 50 means 'no signal' in hist-cal, not 'league-average starter'. Index = 1+(talent-50)/80 then × incumbent 1.06. Mean live QB index is ~1.20. Offense compose gets 0.24 + blend 0.26; defense gets nothing. That is the +7 to +9.
   Evidence: qb_talent_50 resid=2.102 (Δ -7.0337); qb_league resid=-1.0179; mean qb_talent=66.7495; mean qb_index=1.1995; recruiting↔qb_talent r=0.381 (weak)

2. **Offense-layer vs defense-layer asymmetry** — Offense compose gives roster 0.22 + QB 0.24; defense gives roster 0.12 and no QB. If neutralizing offense layers kills the Over and neutralizing defense layers does not (or makes it worse), the inflation is an offense-width / defense-under-response story.
   Evidence: off_layers_league_def_live resid=-8.8034; def_layers_league_off_live resid=20.7778; mean off=1.2143 mean def=1.1215

3. **Recruiting-anchored units are a net coolant on totals, not the Over** — Recruiting is a common factor (r≈0.87 vs every unit) and 65/136 teams sit on the 55 floor. But recruiting_channel_50 barely moves residual, and flattening units to 50 *raises* the Over: defense compose weights F7+secondary 0.44 vs offense OL+skill 0.20, so live units~60 help defense more than they boost offense.
   Evidence: recruiting_field_50 resid=8.6608; recruiting_channel_50 resid=8.958; units_50 resid=11.6508 (worse); game_units_50_indices_live resid=9.104

4. **Recruiting floor at 55 and right tail** — 65 FBS teams sit on the packaged 55 floor; 23 are ≥80. That is real width and a real double-count into units/roster_strength — but it is **not** what prints the +9 total residual (see recruiting_channel_50).
   Evidence: recruiting dist=mean=66.5515 sd=12.6292 p10=55.0 p90=87.0

5. **Full roster/QB/unit league (replication of #538 +0.10)** — Control: live SP+ + league identity should collapse the residual if localization holds.
   Evidence: roster_qb_units_league resid=0.0713

## 6. Next falsifiable experiment (not a ship)

Falsify the QB-talent location claim without fitting to 2026 books or opening 2025: recompute talent_from_qb_stats after zeroing one term at a time (attempt cap, YPA, TD) and after a *formula-internal* recenter that maps the cross-sectional median starter to 50 (location only; preserve rank). Pre-register: if zeroing the attempt term or the median-to-50 map drops W1/W2 residual below +3 while recruiting_channel_50 stays ~+9, the mechanism is the QB counting-stat location, not recruiting/units. Do not ship the recenter. Do not tune the map to street totals.

## 7. What this is not

- Not a λ / Line Curve / global offset proposal.
- Not a 2025 peek. Seal still hard-fails without a 2023–24 freeze.
- Not a retune to UNLV/UNT or the other five 2026 spread outliers.
- Not public CFB. Board stays dark until a mechanism earns green.

JSON: `cfb-2026-roster-inflation-diagnostic-20260911.json`
