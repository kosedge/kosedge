# Affected-delta map — CLEAR 92861 Worker B (#715)

CERT=0. A is sole shared-file writer. Delta review only after eng ACCEPT. No full re-review.
Preserve IDENTITY 81759 tip 7ea9729f / ledger `ce188c64…`.

## Changed vs 7ea9729f

| path | delta |
|---|---|
| `jsonl_trace.py` | **NEW** — 143 JSONL source/value/clock/export from freeze+ADMISSIBLE selected only; staged projection verify |
| `constants.py` | 92861 pins + freeze/81759/staged-143 sha |
| `tests/test_nfl_owned_market_v1.py` | +3 focused (21 total) |
| `CLOCK_LINEAGE_LEDGER_92861.json` | 143 bound rows + 96/400 exact IDs + NOT_EVALUABLE clocks |

Unchanged: risk1 `ca253545…` · 23/44 evidence · freeze#limitations unverified · NTBB-K not implemented.

## Integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q --tb=short
# 21 passed
```

## Remaining blockers

freeze `#limitations` unverified · 143 envelope clocks NOT_EVALUABLE · `pulled_at` not causal.
PARTIAL ≠ owned completion. Identity+value bind ≠ lineage/GO.
