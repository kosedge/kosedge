# VERDICT_ENG — t4885u Stage-1 (engineering self-label only)

**Eng self-label: CONDITIONAL_RECON**

Alex RO is the official `PASS_RECON | CONDITIONAL_RECON | RETURN`. This file is not that grade.

## Why CONDITIONAL (eng)

Holds:

- Selection hash sealed before rebuild; N=31 matches 2017 REG W1–W2 in `games.csv` 4fe1cdd7 (re-hash MATCH).
- Every required `b41f4b43` field classified. Zero silent defaults. Zero sample add/drop.
- Week 1 prior-season/preseason handling is explicit: T5 and T1–T4 are `MISSING_RECORD`; 2016 REG schedule is cited as availability evidence only; later-2017 not used.
- Week 2 cutoffs are each game’s `kickoff_utc`. T5 uses only completed 2017 games with kickoff < target. TB/MIA (no W1 game) stay `MISSING_RECORD` on T5.
- 2024–25 untouched. IF not scored. Odds/API = 0.
- Pins: contract **b41f4b43**, PASS_CONTRACT **1a53bbd3**, as-of **cf514078** / module **7dc6afea**, SOURCE ONLY **52d9e909** (not invoked).

Does not hold for PASS_RECON (eng view):

- 0/31 games are fully reconstructable.
- 16/20 efficiency fields (T1–T4) are `MISSING_RECORD` on every game — no 2016–2017 situational / rolling 5g on box.
- Week 1 T5 is `MISSING_RECORD` (no authorized prior-season baseline).

That is an honest gap, not a fill.

## Not claimed

PASS_RECON · Stage-2 ready · IF accuracy · market beat · CERT · E1.

NFL NO-GO · CERT=0
