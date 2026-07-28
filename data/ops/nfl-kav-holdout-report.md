# NFL KAV Supervised Holdout Report (schema v3)

Generated: 2026-07-28  
Artifact: `data/ops/nfl-kav-supervised-retrain-v3.json`  
DB: `127.0.0.1:5432/kosedge` (restored warehouse; former `kosedge_nfl_restore`)

## Train / holdout design

- **Schema:** v3 (`MODEL_SCHEMA_VERSION=3`)
- **Features:** 41 keys including KAV (`diff_kav_net_5g`, home/away kav offense/defense/net 5g)
- **Split:** chronological — last ~16% of usable rows held out (n_test=570, n_train=2992)
- **Leakage:** KAV joined at week−1 only (week 1 null by design)
- **Seasons in matrix:** 2013–2025 completed games (`rows_seen=3562`)

## Holdout metrics (active fit)

| Metric | Train | Holdout |
| --- | ---: | ---: |
| Brier (home win) | 0.120 | **0.148** |
| Margin MAE | 6.80 | **7.48** |
| Total MAE | 8.84 | **9.20** |

**Gate interpretation:** Holdout clears floors in `docs/NFL_ENTERPRISE_GATES.md`
(Brier ≤ 0.22, margin MAE ≤ 9.5, total MAE ≤ 10.5, schema ≥ 3 + KAV).  
**Status: GREEN** for supervised holdout check alone.

## Caveats (honest)

1. This is in-sample chronological holdout on feature rows — not the same as
   full board re-sim vs market closes for 2025.
2. Blend/calibration retune (2026-07-28) **failed** joint holdout on totals and
   was **not** promoted (`NFL_MARKET_BLEND_*` stays 0.30).
3. Full-slate ATS from prior grading was **0.493** (below −110) — selective
   PLAY publish required regardless of supervised MAE.

## Next measurement

Re-sim 2025 boards with KAV-wired path → `nfl-kav-grading-after.json` →
before/after vs `nfl-kav-grading-before.json` → re-run
`scripts/nfl/evaluate_enterprise_gates.py`.
