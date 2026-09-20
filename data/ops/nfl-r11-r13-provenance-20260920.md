# NFL R11 / R13 provenance receipt — 2026-09-20

**Lane:** provenance / reproducibility only  
**Checkout audited:** `deploy-vercel` @ `4aeab78f` (clean)  
**Verdict:** **FAIL_CLOSED**  
**Exact reproduction established:** no  
**Model edits:** none  
**Holdout run:** none  
**Promotion:** none

Packet: [`docs/ops/NFL_R11_R13_PROVENANCE_LANE_2026-09-20.md`](../../docs/ops/NFL_R11_R13_PROVENANCE_LANE_2026-09-20.md)  
Machine: [`nfl-r11-r13-provenance-20260920/verdict.json`](./nfl-r11-r13-provenance-20260920/verdict.json)

## Slots

| Label | File | Status |
| ----- | ---- | ------ |
| R11 | `nfl-r11-r13-provenance-20260920/r11.lineage.json` | UNBOUND |
| R13 | `nfl-r11-r13-provenance-20260920/r13.lineage.json` | UNBOUND |
| R14 | `nfl-r11-r13-provenance-20260920/r14.lineage.json` | UNBOUND |
| Gate set | `nfl-r11-r13-provenance-20260920/frozen_gate_set.json` | UNBOUND_DIMENSIONS_ONLY |

## Search

See [`nfl-r11-r13-provenance-20260920/search_log.json`](./nfl-r11-r13-provenance-20260920/search_log.json). Labels were not found in repo, git history/tags/worktrees, Linear, Notion, Gmail, Drive titles, or connected private workers.

## Runner

```bash
python scripts/nfl/certify_r11_vs_r14.py
# exits non-zero: FAIL_CLOSED
```

`--execute-holdout` is refused.
