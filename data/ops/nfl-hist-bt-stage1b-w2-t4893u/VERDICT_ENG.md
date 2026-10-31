# VERDICT_ENG — t4893u Stage-1b W2 first (engineering self-label only)

**Eng self-label: CONDITIONAL_RECON**

Alex RO is the official `PASS_RECON | CONDITIONAL_RECON | RETURN`. This file is not that grade. ≠PASS claim.

## Why CONDITIONAL (eng)

Holds:

- Selection hash sealed **before** PBP open / matrix rebuild. Eligible N=14 of 16 W2 games in `games.csv` 4fe1cdd7 (re-hash MATCH).
- Exclusions recorded with the fixed rule: `2017_02_CHI_TB` (TB), `2017_02_MIA_LAC` (MIA). No fills.
- **Complete-game coverage: 14 / 14 eligible games are 27/27 DERIVED_PREGAME.** Cells 378/378. Zero defaults.
- Every matrix cell cites source sha + kickoff cutoff. Leakage audit PASS (15 W1 games / 1830 plays; max consumed kickoff `2017-09-12T02:20:00Z` < min target `2017-09-15T00:25:00Z`).
- T1 is a port of the cited ingest.py SQL. Play filter `pass`/`run`. Pressure = `(sack OR qb_hit)/play_type='pass'`. RZ = play-based `yardline_100<=20` (trips paraphrase refused).
- T2 1-game window accepted as “≤5 played.” T3 consumed at `rating_week=1` only.
- T5 same-season W-L only. 2024–25 untouched. IF not scored. Odds/API credits = 0.
- Pins: contract **b41f4b43**, PASS_CONTRACT **1a53bbd3**, as-of **cf514078** / module **7dc6afea**, PBP **84eacd96**, SOURCE ONLY **52d9e909** (not invoked).
- nflverse EPA retro-fit caveat labeled.

Does not hold for PASS_RECON (eng view):

- T1 numeric verification against a 2023+ backbone T1 table was **not possible** on this box (2023/2025 PBP not owned; 2024–25 not opened). Gate used = code-review port + synthetic fixture only.
- Plain-English “RZ trips” and two home-minus-away paraphrases differ from the cited T1/T3 SQL. SQL was used; Alex must confirm that is “as written.”
- EPA/success are retro-scored metrics.

That is an honest residual, not a fill.

## Not claimed

PASS_RECON · Stage-2 ready · W3–W6 extend · IF accuracy · market beat · CERT · E1.

NFL NO-GO · CERT=0
