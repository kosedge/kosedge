# Affected-delta map — RETURN 36205 / DESIGN 25194 / CLEAR 92861

CERT=0. Isolated NTBB-K numeric/direct boundary. Not a new pool.
Folds incomplete C1–C8 clarifications into this return. A is sole shared-gate registrar.
No market-ledger rewrite. No whole-package close from B.

## vs d0bb6bef (prior kernel tip)

| path | delta |
|---|---|
| `nfl_ntbb_k_v1/constants.py` | RETURN 36205 + DESIGN 25194 pins; `DEMO_SMALL_NINE` rename; exact `ROOT_NINE` |
| `nfl_ntbb_k_v1/law.py` | validate p/c/k **before** t=0 shortcut (NaN/bool refuse) |
| `nfl_ntbb_k_v1/special.py` | remaining-series tail; r+μ collapse refuse; same-p NB(r+1) |
| `nfl_ntbb_k_v1/table.py` | enumeration_error ≤1e-10; interval clip; moment accuracy refuse |
| `nfl_ntbb_k_v1/cases.py` | execute actual root nine; expected N 175/183/174 |
| `nfl_ntbb_k_v1/produce.py` | clarifications MATCH + return/design/future_grad_step |
| `tests/test_nfl_ntbb_k_v1.py` | +7 direct/root/clarification controls |
| `data/ops/nfl_ntbb_k_v1/` | regenerated kernel + RETURN 36205 receipts |

## vs a807af22 (SUPERSEDED held tip)

| path | delta |
|---|---|
| `special.py` | log-PMF domain refuse · NB-tail `max(q,ρ)` · BB rising-factorial refuse |
| `law.py` | untilted betabinom mean check |
| `constants.py` | RETURN 58427 / UNDER 36205 / ADDITIVE 80649 · `LOG_PMF_DOMAIN_TOL` |
| `produce.py` | stamps under/additive ids |
| kernel SHA | `ee800291…` → `bc71269f…` |

Unchanged hashes: 92861 `6879ed43…` · 143 `bf5fd92e…` · 81759 `ce188c64…` · risk1 `ca253545…`. CSV44 not promoted.

Prior maxN 61 / μ 4–12 cases are **DEMO_SMALL_NINE**, not the executed root fixtures.

## Integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_ntbb_k_v1.py tests/test_nfl_owned_market_v1.py -q --tb=short
# 36 passed (REPORTED_ONLY)
```
