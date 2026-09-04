# NCAAM Lab — first frozen scorecard (#14 DAY GO)

**As of:** 2026-09-04
**Branch base:** `cursor/ncaam-lab-fair-engine-21e8` (PR 476) / scorecard follow-up
**Protocol:** `ncaam-fair-lab-protocol-v1.0`
**Scorecard:** `ncaam-fair-lab-scorecard-v1.0`

## Grades (Test-A OOS)

| Pillar | Grade |
| ------ | ----- |
| Predictive Quality | **AMBER** |
| Market Edge Evidence | **AMBER** |
| Evidence Quality | **RED** |

**Subscriber Influence:** **INSUFFICIENT EVIDENCE**

Evidence Quality RED or DATA GAP blocks influence claim; numbers reported honestly — no product flip

## Artifacts

- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.json`
- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.md`
- `docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1.md`
- Fair sets: `ncaam-fair-lab-{train_a,test_a}-latest.parquet`

## Receipts

- Leakage violations: `0`
- SETTLED count: `0`
- Lab joins remain Schedule SoT **D** (ESPN SoT A in PR 477 noted; `slate_complete=false`)
- No retune after Test-A; no Edge>4 shopping; no Edge Board writes

## How to re-run

```bash
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut test_a
python3 apps/web/scripts/lab_ncaam_fair_scorecard.py
```
