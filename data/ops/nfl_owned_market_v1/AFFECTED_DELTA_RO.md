# Affected-delta map — IDENTITY 81759 Worker B (#715)

CERT=0. A tip d3f2c56a PRESERVE. Delta review only after eng ACCEPT. No full re-review.
Preserve EVIDENCE 70648 tip 98ec5d86 / Cos ACCEPT 451ea843.

## Changed vs 8c0a04fb (after Codex stage)

| path | delta |
|---|---|
| `identity_join.py` | **NEW** — exact home/away+kickoff+season/REG join; uniqueness; no slop |
| `constants.py` | 81759 pins |
| `tests/test_nfl_owned_market_v1.py` | +3 focused (18 total) |
| `CLOCK_LINEAGE_LEDGER_81759.json` | 44 associations annotated with proven game_ids |

Unchanged: risk1 `ca253545…` · 187/400 identities · freeze#limitations unverified.

## Integrated command

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q --tb=short
# 18 passed
```

## Remaining blockers

freeze `#limitations` unverified · 143 JSONL unknown · `pulled_at` not causal. Identity success ≠ lineage/GO.
