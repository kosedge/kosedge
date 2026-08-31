# Chapter 2 Phase 1A — compose / eff / QB inputs (still no weight edit)

**Repo:** `kosedge/kosedge`  
**Base:** after Chapter 2 Phase 0 decomposition

Phase 0 locked: TCU raw +19.19 (still ~13.7 at RESPONSE=1.00); HAW@STAN polarity at −9.9 (−6.4 at 1.00). Do **not** “fix” by setting `MATCHUP_RESPONSE=1.00`.

## This PR

Phase 1A only. Decompose `offense_index` / `defense_index` / expected points for UNC, TCU, HAW, STAN into SP+/eff, roster, QB, units, coaching. File:line + values. One recommended lever or blocker. **No product number change.**

## Forbidden

Writes to `compose_team_projection`, `MATCHUP_RESPONSE`, `build_power_sot`, `priors.py` SD, `apply_cfb_kei`. No team ifs. No Utah / NFL/CBB/MLB.
