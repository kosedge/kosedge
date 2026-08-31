# Chapter 2 Phase 0 — raw margin / compose (DISCOVERY ONLY)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after Chapter 1 fit + blockers  
**Engine:** `cfb-season-engine-v0.15-power-sot` (plus short-bucket map 1.188 if that PR merged)

Chapter 1 result (locked): TCU still −20.39 (raw ~19–20); HAW@STAN +10.9 wrong side. One monotonic map cannot fix both. Remaining miss is **expected points**, not WP SD.

## This PR

Phase 0 only. Decompose UNC@TCU and HAW@STAN term-by-term from compose / `expected_team_points` / HFA / units. File:line. No weight edits.

## Forbidden

Any write to `compose_team_projection`, `MATCHUP_RESPONSE`, `build_power_sot`, `apply_cfb_kei`, priors SD. No team ifs. No Utah / NFL/CBB/MLB.
