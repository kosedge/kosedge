# Train-only RZ opportunity repair

The pre-code receipt is `precode-receipt.json`. It freezes the four existing
512-replicate schedules (2,048 games) and the 2013–23 regular-season PBP
input; it contains no held-out, R14, market, or production data.

The trace isolated one exact train-supported interface:

```
nflfastR kick_distance + punt_fair_catch/punt_downed/punt_out_of_bounds/
punt_in_endzone
  -> build_clock_play_coherent_state_priors.py
  -> special_teams.punt priors
  -> ClockPlaySimulator._punt()
```

`punt_yards` is null in the canonical PBP, while the original builder read it
as punt distance and treated terminal no-return flags as returns. The repair
uses `kick_distance` (with legacy fallback), maps those terminal flags before
the zero-return-yard fallback, and accepts the resulting `dead_ball` outcome
in the simulator.

With the exact same 2,048 seeds, RZ entries change from 10.033 to 7.588 per
game (train: 6.454) and RZ opportunities from 33.458 to 25.176 (train:
19.891). Route volume declines from 16.212 to 12.106 pass routes (train:
9.750) and from 13.227 to 10.000 rush routes (train: 7.742). First downs
decline from 4.002 to 2.974 (train: 2.051), fourth arrivals from 4.019 to
3.070 (train: 2.400), TD exits from 5.741 to 4.271 (train: 3.637), and FG
exits from 2.844 to 2.176 (train: 1.831).

The causal check is the entry-origin shift: `punt_return` RZ starts fall from
0.972 to 0.014 per game (train: 0.017). The train-only certification result
for the repaired config is 5.565 offensive TD/game (train: 4.795) and a 48.956
mean total (train: 45.595). It is a materially narrower mismatch, not a gate
clearance; the remaining RZ route excess needs a separately pre-registered
transition/route trace before changing another interface.

Reproduce the repaired trace:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/trace_clock_play_rz_opportunities.py \
  --config data/ops/nfl-clock-play-rz-opportunity-fix/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --historical-pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output /tmp/nfl-clock-play-rz-opportunity-fix-trace.json \
  --source-sha <candidate-sha>
```
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
