# NCAAM Fair Lab Scorecard v1.0

**Protocol:** `ncaam-fair-lab-protocol-v1.0` (LOCKED)
**Scorecard:** `ncaam-fair-lab-scorecard-v1.0`
**Status:** `results_filled`
**Generated:** 2026-09-04T15:38:48.755601+00:00
**Lab:** Kos Edge #14 CBB / NCAAM research fair engine
**Machine JSON:** [`data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.json`](../../data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.json)

> Evidence report only. **No** Edge Board / PLAY / LEAN / Conf% / props.
> **RED = successful** honest failure detection when criteria say so.
> No peek-tuning after Test-A. No Edge>4 shopping.

## Executive grades (Test-A OOS primary)

| Pillar | Grade | Detail |
| ------ | ----- | ------ |
| Predictive Quality | **AMBER** | n=80; B2 MAE 8.8128 vs B1 7.1253 (ratio=1.2368); clears soft AMBER, not market-relative GREEN |
| Market Edge Evidence | **AMBER** | ATS clears (0.5500 n=80) but CLV/ROI soft (CLV+=0.4286 n_clv=42; ROI=0.055) — no Edge>4 shopping |
| Evidence Quality | **RED** | outcome coverage too thin for claimed scorecard (n_actual=80, cov=13.14%) |

**Subscriber Influence (recommendation to CoS → Ryan):** **INSUFFICIENT EVIDENCE**

Evidence Quality RED or DATA GAP blocks influence claim; numbers reported honestly — no product flip

## Locks held

- Baselines **B1** close consensus; **B2** KenPom+HCA + PRIOR/UNKNOWN honesty
- Cuts: Train-A 2022-11-07→2023-03-12; Test-A 2023-11-06→2024-01-28; 2025 pocket OUT
- Schedule Lab joins **D** (Odds `event_id` + B7 fail-closed)
- Continuity PRIOR/UNKNOWN only — never fake SETTLED
- Market Edge open honesty: exclude open timestamp drift >7d
- ESPN Schedule SoT A (PR 477) noted; Lab joins **not** switched (`slate_complete=false`)

## Leakage / continuity receipt

- KenPom leakage OK: `True`
- KenPom leakage violations: `0` (must be 0)
- SETTLED forbidden count: `0` (must be 0)

## Test-A Predictive (B2 vs B1, home-margin space)

| Metric | Value |
| ------ | ----- |
| n lab games | 609 |
| n with actual | 80 |
| outcome coverage | 0.1314 |
| B2 margin MAE | 8.8128 |
| B2 margin RMSE | 12.0952 |
| B2 signed bias | 0.2786 |
| B1 margin MAE | 7.1253 |
| B1 margin RMSE | 10.1622 |
| B2 MAE ≤ B1 | False |
| B2/B1 MAE ratio | 1.2368 |

## Test-A Market Edge (full slate; honest open CLV)

| Metric | Value |
| ------ | ----- |
| filter | `full_slate_no_edge_gt4_shopping` |
| n ATS | 80 |
| ATS | 0.55 |
| ROI (−110) | 0.055 |
| n open honest w/ actual | 80 |
| n CLV move | 42 |
| CLV+ rate | 0.4286 |
| mean CLV move | -0.2175 |

## Test-A Evidence

- Continuity: `{'PRIOR': 609}`
- Open snapshot honest (lab rows): `609`
- PR 477 ESPN Schedule SoT A package exists (slate_complete=false); Lab joins remain Odds event_id + B7 fail-closed for this scorecard

## Train-A diagnostic (context only — not primary grade)

| Metric | Train-A |
| ------ | ------- |
| n lab / n actual | 1119 / 170 |
| B2 MAE / B1 MAE | 10.2948 / 8.3882 |
| ATS / ROI | 0.4201 / -0.2178 |
| CLV+ (n_move) | 0.5641 (78) |

## Hard NOT (held)

- Edge Board / PLAY / Conf% / props
- Odds densify / invent tips / KenPom-as-SoT / #12 GO-2 / squash
- Retune after seeing Test-A

