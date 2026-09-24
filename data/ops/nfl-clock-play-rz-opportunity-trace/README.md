# Clock-Play RZ opportunity-volume trace

This diagnostic freezes the 426c9ac49 coherent-rush configuration and its
four 512-replicate seed schedules (2,048 simulations total). It compares
those replays with the 2013–23 regular-season PBP subset only. It does not
read held-out data, R14, market data, or production services.

The output has a `precode_receipt` for the unmodified candidate config and
decomposes red-zone opportunities by:

- first-entry origin in the possession;
- red-zone state and resolved route;
- first downs and fourth-down arrivals; and
- offensive-touchdown and field-goal exits.

Run:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/trace_clock_play_rz_opportunities.py \
  --config data/ops/nfl-clock-play-rz-opportunity-trace/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --historical-pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output /tmp/nfl-clock-play-rz-opportunity-trace.json \
  --source-sha <candidate-sha>
```
