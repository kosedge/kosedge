# t5107u offline forecast builder + evaluator scaffolding

CERT=0. DRAFT≠merge. RESEARCH_CONSUMED_RETRO. No EXEC scoring.

```
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_forecast_builder_t5107u.py --seal-manifest
```

`--score` is refused. EVAL sequential generation is gated on this sealed FROZEN_MANIFEST plus an explicit flag. CoS one-run bind is not issued here.

Q2 intercept/slope transfer from frozen DEV 2013–16 (training end 2016 ≤ 2021). IF control is retained and labeled archived vs reconstructed; 2020–23 reconstruction is blocked on missing artifacts listed in FROZEN_MANIFEST.
