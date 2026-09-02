# NHL Chapter 3 — situation scorecard

**Stamp:** `nhl-season-engine-v0.1` · schedule `2026-27`  
**Cap:** `NHL_SITUATION_GOAL_CAP = 0.35`  
**Units:** goals / game on Ch1 `GF/G`  
**Brief:** [`docs/NHL_CH3_SITUATION_BRIEF.md`](./NHL_CH3_SITUATION_BRIEF.md)  
**Shrink:** `NHL_TEAM_CARRY_SHRINK = 0.85` **unchanged**

---

## Chosen coefficients (NHL goal paper-sim)

| Class    |                                           Coeff |
| -------- | ----------------------------------------------: |
| home     |                                       **+0.10** |
| b2b      |                                       **−0.15** |
| travel   |                                       **−0.08** |
| altitude | **+0.12** (home at venue) / **−0.12** (visitor) |

Paper-sim: 1344 games / 2688 team-games. Clip rate **0**.  
GF/G′ after Δ on Ch1 lines: **2.40 – 3.82** (band 2.0–4.5).  
Not NBA `home=+2.0` · not WNBA `home=+1.5`.

Prevalence: home 50% · B2B 22% · travel 17% · altitude 6%.

---

## Formula

```text
Δ_raw = Σ class_coeff
Δ     = clip(Δ_raw, ±NHL_SITUATION_GOAL_CAP)   # 0.35
gf_pg' = Ch1_gf/gp + Δ
ga_pg' = Ch1_ga/gp                             # unchanged
if Δ ≠ 0:
  skater G × (gf_pg' / Σ G)                    # copy-through
  goalie SA × (gf_pg' / gf_pg_base)            # shares / SV% / GAA fixed
```

---

## Sample apply-on-read

| Context                          | Flags                     |   ≈ Δ |
| -------------------------------- | ------------------------- | ----: |
| COL home @ Ball Arena            | home + altitude           | +0.22 |
| Visitor @ Ball Arena / Delta     | altitude (−) ± travel/B2B | ≤ cap |
| Home only (no alt / B2B / miles) | home                      | +0.10 |
| B2B road trip (long haul)        | b2b + travel              | −0.23 |

---

## Frozen (untouched)

| Constant                     | Value                  |
| ---------------------------- | ---------------------- |
| `NHL_TEAM_CARRY_SHRINK`      | 0.85                   |
| Ch2 TOI grid + tandem        | on disk                |
| Ch5 `PlayerProjection` means | on disk, not rewritten |
| Raw `nhl_schedule_2026.json` | fetcher pack kept      |
| KEINHL                       | blank / markets-only   |

---

## Gates

| Gate                                      | Result   |
| ----------------------------------------- | -------- |
| GF/GA league-sane after apply             | **PASS** |
| Σ skater G inside residual (disk + apply) | **PASS** |
| Goalie shares ~1.0                        | **PASS** |
| Cap clips extreme stacks                  | **PASS** |
| Altitude = venue list, not team if        | **PASS** |
| KEINHL still blank · no props             | **PASS** |
| NBA / WNBA / CFB untouched                | **PASS** |

**Stop.** Coeffs on read. Board still markets-only.  
**Next:** Chapter 4 KEI emit — PASS until trusted Best. **Not** props.
