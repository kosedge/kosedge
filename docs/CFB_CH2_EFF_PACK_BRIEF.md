# Chapter 2 Phase 2A — efficiency pack (DISCOVERY ONLY)

**Repo:** `kosedge/kosedge`  
**Base:** after #352 low-sample blend  

QB path shipped (do not reopen in this PR):

| Pass | Result |
|---|---|
| 1C taper | OSU 1.389 > HAW 1.377 > TCU 1.372 |
| 1D att/22 | HAW talent 82.23 → 77.89 |
| 1E att<80 → recruiting | STAN talent **50.55 → 66.23** · HAW **77.89 unchanged** · top-7 flat |
| HAW@STAN KEI | +10.84 → **+7.62** still wrong side |
| BALL | −42.05 / cupcake |
| TCU margin | still ~18.7 (338 att, not in 1E) |

Remaining polarity after QB work is **off_eff**: STAN **28.18** vs HAW **50.21**. UNC **24.92** vs TCU **64.74** is the TCU-game twin. This PR only explains those four numbers.

---

## This PR

READ ONLY. Map where `off_eff` / `def_eff` for UNC, TCU, HAW, STAN are built. File:line. Year, opponent adjustment, garbage-time. Do not edit `MATCHUP_RESPONSE`, compose weights, or QB path.

Do not `if team == "Stanford"` or `"Hawaii"` or `"UNC"` or `"TCU"`.  
Do not set `MATCHUP_RESPONSE=1.00`.  
Do not revert 1C/1D/1E.  
Do not touch Utah, NFL/CBB/MLB.

Start with outline + greps, then the four-team eff table.

---

## Required table

| team | off_eff | def_eff | source year(s) | opponent-adjusted? | sample (plays/drives) | known shock (coordinator/portal) |

Then: if STAN 28 and UNC 25 are last-year collapsed offenses with no 2026 update, say so. If they are live 2026, say so.

Recommendation line: **rebuild eff source** vs **leave it** vs **Chapter 3 situation only**.

---

## Forbidden

Any write to efficiency pack, `MATCHUP_RESPONSE`, compose, QB talent, KEI.
