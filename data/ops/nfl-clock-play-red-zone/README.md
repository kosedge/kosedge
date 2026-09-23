# Clock-Play red-zone / goal-to-go transition experiment

This train-only candidate changes only scrimmage transitions at the opponent
20-yard line and closer. It is not a formal baseline, does not clear Gate 1,
and does not authorize R14.

QA gates run before accepting a model result:

1. build `historical-denominator-receipt.json` and match its locked anchors;
2. route every snap exclusively: fourth-down GO → fourth-down continuation;
   otherwise red zone → red-zone transition; otherwise generic;
3. verify drive/possession isolation against the v1.2 parent.

Build the red-zone priors from owned 2013–2023 regular-season PBP:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_red_zone_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-red-zone/red-zone-priors.json
```

The builder pools mutually exclusive urgency × field bucket × goal-to-go ×
down × yards-to-go cells to their red-zone-only parent outcome distribution.
It does not use open-field or aggregate drive rates as shrinkage targets.
