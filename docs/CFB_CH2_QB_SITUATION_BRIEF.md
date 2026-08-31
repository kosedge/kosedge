# Chapter 2 Phase 1B-0 — qb_situation construction (DISCOVERY ONLY)

**Repo:** `kosedge/kosedge`  
**Base:** after #348 compose/QB 1A audit

1A locked:

- TCU expected **36.67** (actual 10): QB **+8.24**, eff +4.13, roster +1.6
- HAW expected **31.81** road: QB **+7.48**, eff **~0**
- UNC 17.48 vs scored 15 — UNC prior fine
- TCU and HAW **identical** `qb_situation_score=80.4` · `qb_index=1.38` **(clamp)**
- Global ±10% QB/eff/roster does not hit desk; QB 0.9 shuffles top-7
- Do **not** cut `MATCHUP_RESPONSE` or `WEIGHT_QB`

## This PR

Read-only. Map `qb_situation.py`: how a team gets score 80.4 and index 1.38. Cap roster for 2026. Why TCU == Hawaiʻi numerically. Schema tier vs broken input. **No product number change.**

## Forbidden

Any write to `qb_situation.py` logic, clamp, compose weights, priors, KEI, power sort. No team ifs. No Utah / NFL/CBB/MLB.
