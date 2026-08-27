# Camp Desk → DepthSotWorkItem handoff (2026-08-27)

**Add the handoff, not auto line moves.**

```
note → SOT FLAG / DepthSotWorkItem → human accept structured pack fields
  → rematerialize → receipt → board
```

## Contract

| Rule | Value |
|------|-------|
| Notes touch means / props / spreads | **Never** |
| Proposed pack patch auto-applies | **Never** |
| Who may write the depth pack | **Accept only** |
| Who may rematerialize | **Accept only** (`--write`, receipt marks remat) |
| Second SoT / second depth map | **Forbidden** |

## Tiers

| Tier | Meaning | SLA |
|------|---------|-----|
| **T1** | Same-day (named starter, season-ending IR/out on pack) | 12h |
| **T2** | Next remat (material flag, human must fill fields) | 48h |
| **T3** | Pass (thin August / do-not-crown; no pack write) | 72h |

Overdue SOT FLAGs stay tickets until accept (or T3 `--allow-empty`).

## Pieces

| Piece | Path |
|-------|------|
| Model | `services/model-service/src/services/nfl_camp_sot_queue.py` (`DepthSotWorkItem`) |
| CLI | `scripts/nfl/queue_camp_sot_flags.py` |
| Queue | `data/ops/nfl-daily-intel/proposed/` |
| Accept → apply | existing `apply_intel_overrides` (one pack) |
| Receipts | `data/ops/nfl-daily-intel/receipts/` |
| Remat | safe rebuild weeks 1–18 (`nfl-spine-safe-rematerialize.md`) |

## Commands

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan
python scripts/nfl/queue_camp_sot_flags.py --queue --tier T1
python scripts/nfl/queue_camp_sot_flags.py --accept data/ops/nfl-daily-intel/proposed/camp-flag-2026-08-26-CLE.json --write --rematerialize
# Then run the receipt's POST /nfl/ops/rebuild-props-layers?season=2026&weeks=1..18
```

Watson Week 1 starter, Higgins ACL, and similar claims must not live only in the
Wednesday wrap — they become T1 work items with a proposed patch until Accept.
