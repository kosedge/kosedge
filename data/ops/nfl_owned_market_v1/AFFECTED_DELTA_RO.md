# Affected-delta map — DELTA 58426 Worker B (#715)

CERT=0. Alex + PE affected-delta only vs changed paths + integrated command.
Reuse Cos ACCEPT ff45970b (risk1 / profiles / no outcome join) and prior PASS papers.

## Changed vs tip 9ce485e9

| path | delta |
|---|---|
| `owned_readiness.py` | probes **git:7834cbc7** originals (not invented destinations); identity projection 187/400 |
| `constants.py` | history pins (7834cbc7, admissible sha, reg496/96/400/187) |
| `schema.py` / `validate.py` | `OWNED_IDENTITIES_PROJECTED`; refuse copied values / invented clock/causes |
| `tests/test_nfl_owned_market_v1.py` | +identity projection test (13 total) |
| `OWNED_187_400_CLOCK_UNAVAILABLE.md` | rewritten to actual original locators |
| fixtures/readiness | identities only; risk1 economic fixture **unchanged** `ca253545…` |

Not restored onto tip as working-tree copies (would expose 2022/23 quote values). Readable via `git show 7834cbc7:<path>`.

## Integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q --tb=short
# 13 passed
```

## Remaining blocker

Clock: `MARKET_ARM_FREEZE.json#limitations` publication/observation timestamps **unverified** on the original. Not invented. No Cos request (187 recovered).
