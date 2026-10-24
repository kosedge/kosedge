# Injury roster leakage inventory v1 (Phase 0)

Ryan t4344u OPTION B (`47afd7f6`). IMV root cause `0feec57e` B-4b(n)-PIT.

Season-level nflverse roster snapshots were collapsed with the `week`
column ignored. Early-season starter / depth / identity / continuity can
use later-week (often playoff) roster information. The package claim
"pre-kickoff information only" is false for rosters.

This deposit documents every residual-fit use of that collapse.
It does not rebuild, refit, or open the holdout.

## Read first

- `STOP.md` — opening path paused
- `INVENTORY.md` — sites, leak, le2023 invalidation
- `sites.json` — machine-readable site list
- `VERIFIED-VS-CLAIMED.md` — what was opened vs inferred
- `evidence/` — Ryan decision + empirical ≤2023 counts

## Phase 1

Week-aware reconstruction spec lives in the sibling deposit
`artifacts/injury-week-aware-roster-spec-v1/`. CoS routes both to IMV.
Do not start a production refit until IMV accepts that spec.
