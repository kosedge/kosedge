# NFL pack vs FantasyPros team mismatches — 2026-08-13

Doctrine: **Reality/market > stale pack.** One SoT after correction.
Source: FantasyPros partners ADP (same feed as the fantasy desk).
This file is **mismatches only**. You review CLEAR_ERROR names and say
`fix these / hold those`. That is the whole human loop.

Re-run: `python3 scripts/nfl/audit_nfl_pack_vs_market.py`

Generated: `2026-08-13T17:55Z`
FP snapshot: `8/05` (fetched `2026-08-05T22:52:14Z`, merged n=518)

## Counts

- Same-team matches in scope: **191**
- Mismatches: **0**
- CLEAR_ERROR: **0**
- NAME_MATCH_WEAK: **0**
- STALE_FP (documented pack overlay / checksum QB): **0**
- Unmatched pack (in scope, no FP name hit): **0**
- FP ADP≤150 not in pack: **0**
- Fantasy CSV vs FP (ADP≤150): **0** (bundle `nfl-preseason-sim-2026-20260813T172000Z`)

## Human loop

**Nothing to fix.** Pack, fantasy CSV, and FantasyPros agree on team for every in-scope skill player after the Walker→KC hotfix.

## Smoke (must hold)

- `kennethwalker` pack=KC want=KC — **PASS**
- `zachcharbonnet` pack=SEA want=SEA — **PASS**
- `mikeevans` pack=SF want=SF — **PASS**
- `emekaegbuka` pack=TB want=TB — **PASS**

## CLEAR_ERROR — pack team ≠ FP team (high-confidence name)

Fix these like Walker: update pack overlay, re-allocate, republish.
Do not bulk-move if the name match looks wrong.

_None._

## STALE_FP — pack has documented newer SoT; FP still elsewhere

Hold unless you confirm FP is right and the overlay is the bug.

_None._

## NAME_MATCH_WEAK — do not bulk-move

_None._

## Fantasy CSV vs FP (ADP≤150)

Desk projection team ≠ FantasyPros team. Dual-map if pack already matches FP.

_None._

## Unmatched pack in scope (no unique FP name hit)

_None._

## FP ADP≤150 not found in pack (sample)

_None._
