# Affected-delta map — EVIDENCE 70648 Worker B (#715)

CERT=0. A tip d3f2c56a PRESERVE — no A work. No full Alex/PE re-review.

## Changed vs start tip 2497a156

| path | delta |
|---|---|
| `clock_lineage.py` | **NEW** — verify staged sha256; expand 44; classify evidenced vs unresolved |
| `constants.py` | 70648 pins (staged sha / 44 / 143) |
| `tests/test_nfl_owned_market_v1.py` | +2 focused tests (15 total) |
| `CLOCK_LINEAGE_LEDGER_70648.json` | source-bound 44 subset + remaining-field reasons |
| `START_PREFLIGHT_EVIDENCE70648_B.md` | GATE0 PASS |

Unchanged: risk1 `ca253545…` · readiness 187/400 · freeze#limitations not marked verified.

## Integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q --tb=short
# 15 passed
```

## Remaining blockers

1. `7834cbc7:…/MARKET_ARM_FREEZE.json#limitations` publication/observation still unverified
2. Odds API `event_id` ↔ freeze `game_id` mapping absent (overlap 0)
3. 143 JSONL clocks preserved unknown
