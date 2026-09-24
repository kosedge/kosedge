# Clock-Play RZ route and transition volume trace

## Pre-code contract

- **Hypothesis:** the residual train-only RZ route-volume excess after the
  punt-prior repair is concentrated in a specific entry-origin × resolved
  play-family chain. If the trace identifies one such chain with a matching
  train PBP denominator and a direct existing builder/simulator interface, a
  bounded follow-up may be considered. Otherwise this remains diagnostic only.
- **Parent:** `7bc1f224dd9115e375c5d511a0d1e9368d185214`, using the repaired
  `nfl-clock-play-rz-opportunity-fix` priors and the four frozen 512-replicate
  seed schedules (2,048 games).
- **Historical denominator:** 2013–2023 regular-season PBP only. Held-out,
  R14, market, and production data are prohibited.
- **Change:** add read-only accounting of RZ routes and their resolved
  transition outcome, jointly keyed by entry origin and play family, plus the
  pre-entry yard line for a route that crosses into the RZ.
- **Frozen:** simulation policy, all train priors, state routing, timing,
  possession semantics, seed schedule, and certification thresholds.

The trace is accepted only if every recorded opportunity has one entry origin,
one resolved route, and at most one terminal transition classification. It
does not authorize a model change by itself. A future candidate must isolate a
single train-supported interface rather than adjust multiple route families.

Run:

```bash
PYTHONPATH=services/model-service python3 \
  scripts/nfl/trace_clock_play_rz_opportunities.py \
  --config data/ops/nfl-clock-play-rz-route-transition-trace/config.json \
  --inputs data/ops/nfl-clock-play-baseline-v1/inputs.json \
  --historical-pbp /path/to/nfl-pbp-audit-input-2013-2025.ndjson \
  --output /tmp/nfl-clock-play-rz-route-transition-trace.json \
  --source-sha <candidate-sha>
```
