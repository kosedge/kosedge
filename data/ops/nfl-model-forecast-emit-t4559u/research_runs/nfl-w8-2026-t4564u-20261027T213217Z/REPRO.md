# t4564u W8 research forecast — repro

CERT_CANDIDATE=0. NFL NO-GO. No Odds. No #641 / F2.

```bash
cd /workspace
PYTHONPATH=services/model-service python3 scripts/nfl/run_w8_research_forecast_t4564u.py
```

Requires network to nflverse GitHub releases (public). Does not read DATABASE_URL.
Does not call The Odds API. Writes `/workspace/ops/nfl_enterprise_green_t4359u/research_runs/<run_id>/` (0444 + SHA256SUMS).
