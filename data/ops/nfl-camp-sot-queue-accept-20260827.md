# Camp Desk → DepthSotWorkItem handoff (2026-08-27)

**Add the handoff, not auto line moves. Queue ≠ remat.**

```
note → SOT FLAG / DepthSotWorkItem → human accept structured pack fields
  → rematerialize → receipt (pack_diff + line_delta) → board
```

## What ships in git

| Keep | Do not commit |
|------|----------------|
| `nfl_camp_sot_queue.py` (`DepthSotWorkItem`) | `queue/runtime/work-item-*.json` day dumps |
| `scripts/nfl/queue_camp_sot_flags.py` | `receipt-*.json`, accept logs |
| tests | Aug 26 camp-flag snapshots |

Generate the queue after merge: `python scripts/nfl/queue_camp_sot_flags.py --queue`

## Contract

| Rule | Value |
|------|-------|
| Notes touch means / props / spreads | **Never** |
| `proposed_patch` auto-applies | **Never** |
| Pack write / remat | **Accept only** |
| reject / no_change | writes **nothing**, no remat |
| Queue idempotent key | `note_id` + `team_id` + `as_of` |

## Tiers / SLA

| Tier | Meaning | SLA |
|------|---------|-----|
| **T1** | Same-day | 12h **or** before next KEI publish (Thu/Fri 16:00 ET) |
| **T2** | Next remat | 48h |
| **T3** | Pass | 72h / `--no-change` |

## Human steps this week

1. `--queue` (runtime only)
2. Accept CLE Watson + HOU Higgins (`--write --rematerialize`)
3. Confirm remat moved those teams’ KEI / props
4. `--no-change` or `--reject` the other T1s so overdue is not a junk pile
