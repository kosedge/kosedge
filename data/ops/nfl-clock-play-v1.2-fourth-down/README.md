# Clock-Play v1.2 fourth-down continuation

This train-only candidate keeps Clock-Play v1.1’s fourth-down decision policy
and replaces only GO-attempt resolution with PBP-derived continuation priors.
It is not a production model, Gate 1 baseline, or authorization for R14.

Build the committed priors from owned 2013–2023 regular-season PBP:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_fourth_down_priors.py \
  --pbp /Users/ryankos/kosedge/.worktrees/nfl-season-engine-status-timeout/data/ops/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-v1.2-fourth-down/continuation-priors.json
```

The builder estimates conversion, touchdown-given-conversion, converted
non-touchdown yards, and failed-attempt yards by urgency × yards-to-go ×
field-position bucket. Sparse cells receive hierarchical shrinkage to their
urgency × yards parent, then the global train sample.

Freeze with the unchanged structural cases and seed manifest:

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_clock_play_baseline_v1.py \
  --config data/ops/nfl-clock-play-v1.2-fourth-down/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --output-dir /tmp/nfl-clock-play-v1-2-fourth-down-freeze \
  --source-sha <SOURCE_SHA>
```
