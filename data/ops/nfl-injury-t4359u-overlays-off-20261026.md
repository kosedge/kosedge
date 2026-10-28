# PR 611 × t4359u — overlays remain OFF

**PR:** https://github.com/kosedge/kosedge/pull/611 (DRAFT)  
**Decision:** `DECISION_RYAN_t4359u_NFL_ENTERPRISE_GREEN_EXECUTION_PROGRAM_v1`  
**Date:** 2026-10-26  
**Scope:** Injury groundwork only. No overlay unlock. No holdout open. No merge. No deploy.

## Lock

| Item | State |
|------|--------|
| Overlays | OFF (`force_overlays_off=true`, `unlock_overlays=false`) |
| NR-1 | CLOSED MISSING — do not repeat the search |
| Step 3 | FROZEN |
| Step 4 | BLOCKED |
| 2024–25 holdout | SEALED |
| Unknown injury as zero | REFUSED |
| Injury-free baseline | Separate IMV scope; not represented as sourced 0.0 |

Code: `t4359u_injury_program_lock()` and `refuse_unknown_injury_as_zero()` in `nfl_injury_null_contract.py`.

## What this revision adds

- Program lock helper + tests (overlays stay off under t4359u)
- E-2 stale-baseline test: published markets are not mutated when injury is null
- This note

## What this revision does not do

- Does not enable injury overlays or KEI beat
- Does not open 2024/2025
- Does not change K-2 pinned hashes
- Does not rerun accepted W4–W6 seals
- Does not invent T7 / ADD141 Q9 answers (those live on the spec/pipeline PR)

Spec/pipeline work is a **separate** PR so injury overlays-off stays reviewable on its own.

## t4366u

T7 is first in Ryan’s queue. This PR does **not** change the frozen T7 expectation or the overview null-week assertion (`test_prior_season_null_week_cap_sql_is_typed`). Continue overlays-off groundwork only. No holdout, no deploy, no spend.
