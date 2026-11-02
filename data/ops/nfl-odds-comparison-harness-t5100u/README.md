# Synthetic NFL odds comparison harness (t5100u)

CERT=0. DRAFT ≠ merge. Synthetic forecasts and synthetic outcomes only.

Connects the accepted Package A reader (`services/model-service/src/services/nfl_odds_reader.py`) to a frozen forecast file and a matching owned-odds manifest. Invalid inputs are refused or excluded. Comparisons are never fabricated. No paid Odds, no 2024–25 open, no fitting, no scoring, no real-outcome EVAL.

## Example command

From the repo root:

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_odds_comparison_harness.py \
  --forecasts data/ops/nfl-odds-comparison-harness-t5100u/fixtures/example-forecasts.json \
  --odds-manifest data/ops/nfl-odds-comparison-harness-t5100u/fixtures/example-odds-manifest.json \
  --output data/ops/nfl-odds-comparison-harness-t5100u/example-output.json
```

Saved example output: `data/ops/nfl-odds-comparison-harness-t5100u/example-output.json`

## Inputs

- Forecast file schema: `nfl-odds-comparison-forecast-v1` with `label=SYNTHETIC`, `purpose=synthetic_comparison_only`, `cert_candidate=0`
- Odds manifest schema: `nfl-odds-comparison-manifest-v1` with the same synthetic header, plus `games` and `quotes`
- Outcomes, if present, must set `source=synthetic`

## Tests

```bash
cd services/model-service && PYTHONPATH=. python -m pytest tests/test_nfl_odds_comparison_harness.py -q
```
