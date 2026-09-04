# Chapter 2 Phase 0 — raw margin / compose (DISCOVERY ONLY)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after Chapter 1 fit + blockers  
**Engine:** `cfb-season-engine-v0.15-power-sot` (plus short-bucket map 1.188 if that PR merged)

Chapter 1 result (locked): TCU still −20.39 (raw ~19–20); HAW@STAN +10.9 wrong side. Remaining miss is **expected points**, not WP SD.

## This PR

Phase 0 only. Mandatory live decomposition tables for UNC/TCU/HAW/STAN + both games. File:line. No weight edits.

## Forbidden

Any write to `compose_team_projection`, `MATCHUP_RESPONSE`, `build_power_sot`, `apply_cfb_kei`, priors SD. No team ifs. No Utah / NFL/CBB/MLB.
