# NCAAM Lab — scorecard v1.1 fill (#14 Lab scorecard v1.1 fill GO)

**As of:** 2026-09-04
**Base:** `deploy-vercel` @ `8d555eda` (PR 480 B7) + `a616e828` (PR 479 densify)
**Protocol:** `ncaam-fair-lab-protocol-v1.0` (unchanged)
**Scorecard:** `ncaam-fair-lab-scorecard-v1.1`

## Grades (Test-A OOS)

| Pillar | Grade |
| ------ | ----- |
| Predictive Quality | **AMBER** |
| Market Edge Evidence | **AMBER** |
| Evidence Quality | **GREEN** |

**Subscriber Influence:** **INSUFFICIENT EVIDENCE**

Mixed / soft pillars — no influence claim

## Coverage n

- Test-A: `2205 / 2298` (cov `0.9595`)
- Train-A: `3583 / 3676` (cov `0.9747`)


## Test-A pillar numbers (coverage n)

| Pillar | Key numbers |
| ------ | ----------- |
| Predictive | n=`2205/2298`; B2 MAE=`9.248` vs B1=`8.5703` (ratio `1.0791`); bias=`-0.0728` |
| Market Edge | full-slate ATS=`0.5305` n=`2200`; ROI=`0.014`; CLV+=`0.5012` n_clv=`1676` |
| Evidence | cov=`0.9595`; leakage=`0`; SETTLED=`0` |
| Influence | `INSUFFICIENT EVIDENCE` |

## Honest compare to v1 (no threshold shopping)

- v1 Test-A coverage: `80 / 609` (13.14%) → v1.1: `2205 / 2298` (0.9595)
- v1 Train-A coverage: `170 / 1119` (15.19%) → v1.1: `3583 / 3676` (0.9747)
- Same cuts / B1+B2 / gates; deltas = denser results-join + B7 alias expand only
- Grades reported under pre-registered gates; RED remains success when criteria say so

## Artifacts

- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.1.json`
- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.1.md`
- `docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1_1.md`
- Fair sets: `ncaam-fair-lab-{train_a,test_a}-latest.parquet` (rematerialized)
- Frozen v1 thin-join artifacts **untouched**

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
