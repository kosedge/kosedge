# Chapter 2 Phase 1D — talent_from_qb_stats volume (no team if)

**Repo:** `kosedge/kosedge`  
**Base:** after 1C soft ceiling (`apply_qb_situation_soft_ceiling`, τ=0.16)  
**Stamp start:** `cfb-season-engine-v0.15-power-sot` + 1C taper

1C locked: OSU published 1.389 > HAW 1.377 > TCU 1.372. TCU margin 19.01. HAW@STAN still wrong side. Soft ceiling will **not** flip Hawaii. This PR attacks the **talent input**: volume-heavy 2025 attempts.

## This PR

Change the **attempt term only** in `talent_from_qb_stats`. Re-materialize 2026 QB talent. Keep 1C taper. Top-7 frozen. Hawaii flip not required.

## Forbidden

Team ifs. Clamp haircut. `WEIGHT_QB` / `MATCHUP_RESPONSE`. Editing 1C τ. Utah / NFL/CBB/MLB.
