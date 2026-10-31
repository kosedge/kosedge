# VERDICT_ENG — t4893u Stage-1b W3–W6 (engineering self-label only)

**Eng self-label: CONDITIONAL_RECON**

Alex RO is the official `PASS_RECON | CONDITIONAL_RECON | RETURN`. This file is not that grade. ≠PASS claim.

## Why CONDITIONAL (eng)

Holds:

- Selection hashes sealed **before** PBP open / matrix rebuild (commit `32f9a3ec`; PBP path absent at seal). Eligible N=60 of 60 W3–W6 games in `games.csv` 4fe1cdd7 (re-hash MATCH). Exclusions 0.
- Combined selection_hash `e03c96…`. Per-week hashes recorded.
- **Complete-game coverage: 56 / 60 eligible games are 27/27 DERIVED_PREGAME.** Cells 1576/1620 DERIVED; 44 MISSING_RECORD; zero defaults / fills.
- W3 16/16 · W4 16/16 · W5 14/14 complete. W6 10/14 complete.
- Every matrix cell cites source sha + kickoff cutoff. Leakage audit PASS (77 W1–W5 REG games / 9619 pass+run plays; 0 W6 plays; week gaps hold; per-target window week ≤ rating_week and kickoff < target).
- T1–T4 reused from W2 builder (`t1_from_plays`, `rolling_5g`, `lookup_t2`, synthetic fixture). Play filter `pass`/`run`. Pressure = `(sack OR qb_hit)/play_type='pass'`. RZ = play-based `yardline_100<=20` (trips paraphrase refused).
- W1 T1 numeric identity vs W2 packet: max abs diff **0**.
- T5 same-season W-L only. rest_days = same ET DOW heuristic as W2. 2024–25 untouched. IF not scored. Odds/API credits = 0.
- Pins: contract **b41f4b43**, PASS_CONTRACT **1a53bbd3**, as-of **cf514078** / module **7dc6afea**, PBP **84eacd96**, SOURCE ONLY **52d9e909** (not invoked).
- nflverse EPA retro-fit caveat labeled.
- W2 lineage: tip `440314e4` · Alex PASS_RECON `91e2d7db`.

Does not hold for PASS_RECON (eng view):

- **4 W6 eligible games are partial** because W2 `lookup_t2` is exact `rating_week` and those homes (ATL, DEN, NO, WSH) were on bye in W5. Fail-closed MISSING_RECORD on that side’s 5 T1 fields + 6 T4 diffs (11 cells × 4 = 44). Last-played-week T2 was **not** applied (would be a new lookup transform). Alex call.
- T1 numeric verification against a 2023+ backbone T1 table was **not possible** on this box (same residual as W2).
- EPA/success are retro-scored metrics.

That is an honest residual, not a fill.

## Not claimed

PASS_RECON · Stage-2 ready · extend beyond W6 · IF accuracy · market beat · CERT · E1.

NFL NO-GO · CERT=0
