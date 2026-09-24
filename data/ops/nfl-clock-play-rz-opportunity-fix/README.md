# Clock-Play RZ opportunity punt-prior fix

The pre-code trace established that the committed candidate started
0.972 red-zone entries per simulated game from punt returns, versus 0.017 in
the 2013–23 train PBP. Its special-teams builder read the absent
`punt_yards` field and ignored the nflfastR `punt_fair_catch`, `punt_downed`,
and `punt_out_of_bounds` terminal flags.

This isolated candidate re-estimates only the special-teams artifact using:

- `kick_distance` as the punt flight distance; and
- nflfastR punt terminal-state flags before classifying a zero-yard return.

The pass-state data remains the committed coherent-pass artifact. The config
preserves the same four root seeds and 512 replicates per case (2,048 games).
It is train-only: no held-out data, R14, market data, or production service.

Build and trace:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/build_clock_play_coherent_state_priors.py \
  --pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output data/ops/nfl-clock-play-rz-opportunity-fix/coherent-state-priors.json

PYTHONPATH=services/model-service python3 \
  scripts/nfl/trace_clock_play_rz_opportunities.py \
  --config data/ops/nfl-clock-play-rz-opportunity-fix/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --historical-pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output /tmp/nfl-clock-play-rz-opportunity-fix-trace.json \
  --source-sha <candidate-sha>
```
