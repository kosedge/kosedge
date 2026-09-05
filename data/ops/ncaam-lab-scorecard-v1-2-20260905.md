# NCAAM Lab — scorecard v1.2 fill (#14 Path A odds lake backfill GO)

**As of:** 2026-09-05
**Base:** `deploy-vercel` + Path A odds lake backfill (#14 FULL GO)
**Protocol:** `ncaam-fair-lab-protocol-v1.0` (unchanged)
**Scorecard:** `ncaam-fair-lab-scorecard-v1.2`

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

## Honest compare to v1.1 (no threshold shopping)

- v1.1 Test-A coverage: `2205 / 2298` (0.9595) → v1.2: `2205 / 2298` (0.9595)
- v1.1 Train-A coverage: `3583 / 3676` (0.9747) → v1.2: `3583 / 3676` (0.9747)
- v1.1 Test-A Predictive AMBER (B2 MAE 9.248 / B1 8.5703) → v1.2: B2 `9.248` / B1 `8.5703` grade `AMBER`
- v1.1 Market Edge AMBER (ATS 0.5305 / CLV+ 0.5012) → v1.2: ATS `0.5305` / CLV+ `0.5012` grade `AMBER`
- Same cuts / B1+B2 / gates; delta = denser Path A odds lake (honesty-clean) only
- Grades reported under pre-registered gates; RED remains success when criteria say so
- B2 quarantined; Board/PLAY dark; Influence only if gate clears

## Artifacts

- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.2.json`
- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.2.md`
- `docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1_2.md`
- Fair sets: `ncaam-fair-lab-{train_a,test_a}-latest.parquet` (rematerialized; cuts frozen)
- Frozen v1 / v1.1 artifacts **untouched**

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
