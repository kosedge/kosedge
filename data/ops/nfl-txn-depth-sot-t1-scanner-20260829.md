# Free NFL txn → DepthSot T1 scanner (2026-08-29)

**Landed via Desk OS item B** (`cursor/desk-os-item-b-morning-loop-7234`). Supersedes open #300.

## Contract

- Sleeper / optional PFR are **signals**, never writers of means/props/spreads.
- Diff vs live pack `injury_status` → `proposed_patch` only.
- Never invent WR1/QB1 / depth_order from Sleeper depth.
- Never close ATL-style open races.
- No auto-accept.

## CLI

```bash
python scripts/nfl/queue_camp_sot_flags.py --scan-txns
python scripts/nfl/queue_camp_sot_flags.py --morning   # scan-txns + scan-report + alert-t1
python scripts/nfl/ingest_nfl_transactions.py --scan
```

See `data/ops/nfl-desk-os-item-b-morning-publish-20260829.md`.
