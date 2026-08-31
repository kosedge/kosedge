# Chapter 2 Phase 2B — 2025 SP+ carry shrink (global)

**Repo:** `kosedge/kosedge`  
**Base:** after Phase 2A eff-pack audit  

2A locked:

- Compose `off_eff`/`def_eff` = **final-2025 SP+** z-scored to 5–95  
- Pack: `cfb_efficiency_snapshot_2025_carry_2026.json` · `prior_year=2025` · **no 2026 games**  
- Warehouse PBP adj is **research_prior only** — not the line  
- UNC **24.92** (SP+ off 17.2, #124) and STAN **28.18** (18.5, #117) are **2025 corpses**  
- TCU **64.74** / HAW **50.21** are the same carry (strong / average)  
- Portal/QB 2026 does **not** rematerialize eff  

Do not set `MATCHUP_RESPONSE=1.00`. Do not `if Stanford`.

---

## This PR

Phase 0: print `off_eff` for OSU, BALL, TCU, UNC, HAW, STAN, plus top-7. No edits.

Phase 1: ONE global shrink/blend of 2025 SP+ carry toward 50 (or toward packaged roster identity if Phase 0 names that field). Recompute compose canaries.

```text
off_eff' = 50 + shrink * (off_eff_2025 - 50)
def_eff' = 50 + shrink * (def_eff_2025 - 50)
```

`shrink` in (0,1), **one number**. Paper-sim ∈ {0.70, 0.80, 0.85} **before** writing the pack. If 0.70 reorders top-7, try 0.85. If none work, blocker — do not invent 0.40.

---

## Forbidden

Team branches. `WEIGHT_OFF_EFF` / `MATCHUP_RESPONSE`. QB packager. Enabling PBP adj as live KEI SoT. Revert 1C/1D/1E. Utah / NFL/CBB/MLB.
