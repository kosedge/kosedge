# CFB Chapter 2 Phase 2B — 2025 SP+ carry shrink

**Stamp:** `cfb-season-engine-v0.15-power-sot` + 1C–1E QB path  
**Brief:** `docs/CFB_CH2_EFF_CARRY_BRIEF.md`  
**Result:** **BLOCKER** — no pack write

---

## Phase 0 — off_eff table (no edits)

Live universe = packaged final-2025 SP+ carry (`cfb_efficiency_snapshot_2025_carry_2026.json`).

| team | off_eff | def_eff |
| ---- | ------: | ------: |
| OSU  |   76.01 |   95.00 |
| BALL |   15.40 |   30.51 |
| TCU  |   64.74 |   56.29 |
| UNC  |   24.92 |   53.13 |
| HAW  |   50.21 |   47.78 |
| STAN |   28.18 |   44.37 |
| ORE  |   81.02 |   85.97 |
| MISS |   84.02 |   71.86 |
| MIA  |   68.49 |   81.35 |
| IU   |   83.02 |   92.29 |
| TAMU |   77.51 |   74.54 |
| ND   |   82.02 |   74.78 |

**Top-7 power (baseline live `build_power_sot`):** OSU, ORE, MISS, MIA, IU, TAMU, ND  
(ORE 1.5481 / MISS 1.5479 — 0.0002 apart; ND 1.4927 / TEX 1.4897 — 0.003 apart.)

**Blend target named:** league **50** (preferred). Roster identity is already a separate compose weight (`WEIGHT_ROSTER_STRENGTH`); blending eff toward roster would double-count — not used.

**Baseline games (1E locked):**

| Game | model margin (home) | KEI home | WP |
| ---- | ------------------: | -------: | --: |
| BALL@OSU | −40.85 | −42.05 | 0.98 |
| UNC@TCU (n) | −16.48 | −17.68 | 0.90 |
| HAW@STAN | +6.62 (HAW fav) | +7.62 | 0.34 |

---

## Phase 0 paper-sim — `eff' = 50 + s*(eff−50)`

Recompose all teams with shrunk `EfficiencyProfile`, then live `build_power_sot` + `project_game_preview` + `apply_cfb_kei`. **No pack write.**

| s | STAN | UNC | TCU | HAW | OSU | BALL@OSU WP | TCU margin | HAW@STAN KEI | top-7 |
| --: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **0.70** | 34.73 | 32.44 | 60.32 | 50.15 | 68.21 | 0.973 | **13.70** | +5.08 | **REORDER** OSU,MISS,ORE,MIA,TAMU,**TEX**,IU |
| **0.80** | 32.54 | 29.94 | 61.79 | 50.17 | 70.81 | 0.977 | **14.64** | +5.63 | **REORDER** OSU,MISS,ORE,MIA,TAMU,IU,**TEX** |
| **0.85** | 31.45 | 28.68 | 62.53 | 50.18 | 72.11 | 0.979 | **15.11** | +5.90 | **REORDER** OSU,MISS,ORE,MIA,TAMU,IU,**TEX** |

### Gate matrix

| Gate | 0.70 | 0.80 | 0.85 |
| ---- | ---- | ---- | ---- |
| Top-7 power order unchanged | **FAIL** | **FAIL** | **FAIL** |
| BALL@OSU cupcake WP ≥ 0.90 | PASS | PASS | PASS |
| HAW off_eff ~50 | PASS | PASS | PASS |
| STAN off_eff > 28.18 | PASS | PASS | PASS |
| UNC off_eff > 24.92 | PASS | PASS | PASS |
| TCU off_eff < 64.74 | PASS | PASS | PASS |
| TCU raw margin < 16.48 | PASS | PASS | PASS |
| HAW@STAN KEI report (flip not required) | +5.08 | +5.63 | +5.90 |
| OSU still #1 | PASS | PASS | PASS |

Report-only (not allowed by brief — outside {0.70,0.80,0.85}): even **s=0.98** swaps ORE↔MISS (near-tie); membership of the seven holds only for s ≳ 0.98. **Do not invent 0.40** (more aggressive) or 0.98 (outside paper-sim set).

---

## BLOCKER

**Nothing in {0.70, 0.80, 0.85} keeps top-7 power order and moves STAN/UNC.**

Mechanism: global shrink toward 50 compresses SP+ gaps; TEX (baseline #8, mid off_eff 64.5) overtakes ND (#7, high off_eff 82) once elite offense carry is pulled in. ORE/MISS also swap (already a 0.0002 power tie).

Eff-side polarity still wants regression (STAN/UNC up, TCU down all pass at every s). Cupcake survives. The **blocker is the top-7 order canary**, not the corpse move.

### Not done in this PR

- No write to `cfb_efficiency_snapshot_2025_carry_2026.json`
- No `EFF_CARRY_SHRINK` in `priors.py` / `efficiency.py`
- No KEI re-emit
- No `MATCHUP_RESPONSE` / `WEIGHT_OFF_EFF` / team if / QB revert / PBP SoT swap

### Operator next (outside this PR)

Separate design choice, not inventing s:

1. Relax top-7 canary to **OSU #1 + same seven membership** (still fails 0.70–0.85; TEX in), or  
2. Couple a weaker carry shrink with another global lever (not team if), or  
3. Leave 2025 corpses; treat HAW@STAN / TCU margin as Chapter 3 situation / other spine — **not** preferred by 2A.

---

## Forbidden check

No `if team == Stanford/UNC/Hawaii/TCU`. No `MATCHUP_RESPONSE=1.00`. No 1C/1D/1E revert. No warehouse PBP as live KEI SoT. No Utah / NFL/CBB/MLB. No invented shrink outside the paper-sim set.
