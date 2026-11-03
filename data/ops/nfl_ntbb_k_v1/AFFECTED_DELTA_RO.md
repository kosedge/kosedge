# Affected-delta map — NTBB-K SYNTHETIC 92861 / METADATA 14083

CERT=0. Isolated kernel. A is sole shared-gate registrar. No market-ledger rewrite.

## New vs e7084587

| path | delta |
|---|---|
| `services/model-service/src/services/nfl_ntbb_k_v1/` | **NEW** stdlib law + conditional normalizer + tail/moment + nine cases |
| `tests/test_nfl_ntbb_k_v1.py` | +8 focused |
| `data/ops/nfl_ntbb_k_v1/` | kernel document + receipt |

Unchanged hashes: 92861 `6879ed43…` · 143 `bf5fd92e…` · 81759 `ce188c64…` · risk1 `ca253545…`.

## Integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_ntbb_k_v1.py tests/test_nfl_owned_market_v1.py -q --tb=short
# 29 passed
```
