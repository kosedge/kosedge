# Affected-delta map — RETURN 47318 Worker B (#715)

CERT=0. For Alex + PE affected-delta RO vs changed paths + actual integrated command.
Reuse prior reviews (Alex PASS 64dfebc0 / Cos ACCEPT 0c0aab8c · PE PASS d68253ad / Cos ACCEPT e205bee7).
No full re-audit.

## Changed paths (this tip vs f6566c92)

| path | delta |
|---|---|
| `services/model-service/src/services/nfl_owned_market_v1/arithmetic.py` | **NEW** — risk1 ATS / American profit / ROI / line-CLV + missing-data refuse |
| `services/model-service/src/services/nfl_owned_market_v1/owned_readiness.py` | **NEW** — 187/400/clock probe; never claims owned completion |
| `services/model-service/src/services/nfl_owned_market_v1/produce.py` | lineup/weather/liquidity **removed**; risk1 tickets + readiness produce |
| `services/model-service/src/services/nfl_owned_market_v1/validate.py` | owned refuses fictional `observations`; economic binds settlement arithmetic |
| `services/model-service/src/services/nfl_owned_market_v1/schema.py` | roles OWNED_READINESS vs FICTIONAL_ECONOMIC |
| `services/model-service/src/services/nfl_owned_market_v1/constants.py` | return pins; event types = settlement; no play/lean chrome |
| `services/model-service/tests/test_nfl_owned_market_v1.py` | arithmetic + separation + unavailable |
| `data/ops/nfl_owned_market_v1/fixtures/*` | readiness + risk1 replace week-99 quote fiction |
| `data/ops/nfl_owned_market_v1/OWNED_187_400_CLOCK_UNAVAILABLE.md` | exact path/field UNAVAILABLE |

Unchanged ownership: B does not edit `nfl_ops_v1_evidence/*` or register gates.

## Actual integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q --tb=short
PYTHONPATH=services/model-service python3 -m src.services.nfl_owned_market_v1.run --repo-root .
```

## Not in this delta

Historical performance, outcome join, real forecasts, scientific GO, Cos-host runs, shared-gate registration, merge/cert.
