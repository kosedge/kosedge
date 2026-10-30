# STANDBY — t4770u DATA_READY (after W8 final)

Authority: DECISION `751dd63c` · IMV **DATA_PARTIAL_ACCEPT** `c674da77` · contract `b41f4b43` · CoS STANDBY `71a49789`

Accepted tip `ba9e8426` is **through-W7 only**. Do **not** claim DATA_READY. Do **not** merge #663. Do **not** emit.

## Hold until

W8 is 14/14 final, including MNF `2026-W08-CHI@SEA` (kickoff 2026-11-03T01:15:00Z), and nflverse PBP is re-fetchable.

## Then execute (fail closed if still incomplete)

1. **O-a** Re-fetch `play_by_play_2026.parquet` (no `--skip-fetch`). Archive raw bytes + pin `fetched_at_utc`.
2. **O-b** Rebuild through-W8 panel. Recompute T5 W-L through W8. Do not use 2025 priors. Do not invent scores.
3. **O-c** Re-run `prove_if_consume_2026_w09_t4770u.py` (20-field call graph + input-hash perturbation) at the new tip.
4. **O-d** Write / review `rest_days_spotcheck.json` (UTC DOW heuristic; flag UTC↔ET mismatches and short weeks).
5. Seal `DATA_READY` **or** `DATA_PARTIAL` / `DATA_UNAVAILABLE` if W8 is still incomplete. Report tip sha8.

```bash
python3 scripts/nfl/check_w8_complete_t4770u.py --fetch
# only if through_w8_complete=true and MNF present:
python3 scripts/nfl/build_efficiency_2026_w1_w8_t4770u.py
python3 scripts/nfl/prove_if_consume_2026_w09_t4770u.py
cd services/model-service && python3 -m pytest tests/test_nfl_efficiency_2026_w1_w8_t4770u.py -q
```

Until then: IDLE. RO prep on this lane only. ≠emit ≠E2 ≠C10 ≠CERT ≠merge #663.
