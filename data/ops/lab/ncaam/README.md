# NCAAM Lab fair artifacts

Protocol twin + Train-A / Test-A fair parquet manifests + scorecards.
See `docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md`,
`docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1.md` (frozen thin join),
`docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1_1.md` (results densify + B7 expand),
`docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1_2.md` (Path A odds lake densify),
`data/ops/ncaam-lab-first-scorecard-20260904.md`,
`data/ops/ncaam-lab-scorecard-v1-1-20260904.md`, and
`data/ops/ncaam-lab-scorecard-v1-2-20260905.md`.

Results densify receipt: `data/ops/ncaam-lab-results-densify-20260904.md`.
B7 alias expand: `data/ops/ncaam-b7-alias-expand-20260904.md`.
Odds lake Path A backfill: `data/ops/ncaam-odds-lake-backfill-20260905.md`.

```bash
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut test_a
python3 apps/web/scripts/lab_ncaam_fair_scorecard.py              # freeze v1.2
python3 apps/web/scripts/lab_ncaam_fair_scorecard.py --no-densify  # v1 thin baseline
python3 apps/web/scripts/lab_ncaam_results_coverage_receipt.py
```
