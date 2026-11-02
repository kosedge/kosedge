# t5107u / t5108u offline forecast builder + evaluator

CERT=0. DRAFT≠merge. RESEARCH_CONSUMED_RETRO. No EXEC scoring.

```
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_forecast_builder_t5107u.py --seal-manifest
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_forecast_builder_t5107u.py --prepare-inputs --append-bindings
```

`--score` is refused. Design seal `e5bb682d` is **not** a forecast freeze. Real EVAL is gated on a persistent one-run bind + Alex GO + CoS.

Q2 intercept/slope transfer from frozen DEV 2013–16 (training end 2016 ≤ 2021). IF μ is **produced** from frozen tree `6ca03716` when a complete DERIVED_PREGAME packet exists; supplied reconstructed μ is refused. Efficiency/index 5g fields are MISSING (not invented).
