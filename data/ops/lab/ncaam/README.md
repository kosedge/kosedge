# NCAAM Lab fair artifacts

Protocol twin + Train-A / Test-A fair parquet manifests + first scorecard.
See `docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md`,
`docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1.md`, and
`data/ops/ncaam-lab-first-scorecard-20260904.md`.

```bash
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut test_a
python3 apps/web/scripts/lab_ncaam_fair_scorecard.py
```
