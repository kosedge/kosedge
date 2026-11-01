# t5100u harness delivery — synthetic NFL odds comparison

**CERT=0. DRAFT ≠ merge.**

Owner CLEAR tip `4f3b9666` (parent `02ca8367`).  
Alex PASS_RO `db8d27a2` of Package A (#689 @ `f6b5b4c3`).  
CoS scoped draft ACCEPT tip `7f9f7918`.  
Paid Odds pauses stand (`783c286f` + `0c5c52ab`).

## What landed

Sibling branch off Package A tip `f6b5b4c3ec4021fc64d86a36c863b483246be78b`:

- Reader reused, not rewritten: `services/model-service/src/services/nfl_odds_reader.py`
- Harness: `services/model-service/src/services/nfl_odds_comparison_harness.py`
- CLI: `scripts/nfl/run_nfl_odds_comparison_harness.py`
- E2E path tests: `services/model-service/tests/test_nfl_odds_comparison_harness.py`

Synthetic forecasts and synthetic outcomes only. No paid pulls. No 2024–25 open. No fitting / scoring / retuning / real-outcome EVAL. Invalid inputs refuse or exclude; comparisons are never fabricated.

## Example command + saved output

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_odds_comparison_harness.py \
  --forecasts data/ops/nfl-odds-comparison-harness-t5100u/fixtures/example-forecasts.json \
  --odds-manifest data/ops/nfl-odds-comparison-harness-t5100u/fixtures/example-odds-manifest.json \
  --output data/ops/nfl-odds-comparison-harness-t5100u/example-output.json
```

Saved output: `data/ops/nfl-odds-comparison-harness-t5100u/example-output.json`

## Tests

```
cd services/model-service && PYTHONPATH=. python -m pytest \
  tests/test_nfl_odds_comparison_harness.py tests/test_nfl_odds_reader.py -q
......................  22 passed
```

E2E paths covered: H/A signs · incompatible lines · duplicate games · missing probabilities · ties/pushes · post-cutoff quotes · ambiguous identities · invalid-input refusal.

## Bound

Draft PR only. CERT=0. Do not merge.
