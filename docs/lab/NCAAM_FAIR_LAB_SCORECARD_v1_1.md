# NCAAM Fair Lab Scorecard v1.1

**Protocol:** `ncaam-fair-lab-protocol-v1.0` (LOCKED)
**Scorecard:** `ncaam-fair-lab-scorecard-v1.1`
**Status:** `results_filled`
**Generated:** 2026-09-04T17:42:17.162719+00:00
**Lab:** Kos Edge #14 CBB / NCAAM research fair engine
**Machine JSON:** [`data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.1.json`](../../data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.1.json)

> Evidence report only. **No** Edge Board / PLAY / LEAN / Conf% / props.
> **RED = successful** honest failure detection when criteria say so.
> No peek-tuning after Test-A. No Edge>4 shopping.

## v1.1 vs v1.0 (honest delta — no gate shopping)

- Same protocol cuts, baselines B1+B2, frozen grade gates
- Allowed deltas only: denser Schedule SoT results-join (PR 479) + expanded B7 aliases / ESPN packs remapped (PR 480)
- Does **not** claim new Lab windows from Odds densify
- Frozen v1 thin-join artifacts remain untouched

**Version note:** v1.1 fill: same protocol cuts/gates/baselines as v1.0; allowed deltas = denser Schedule SoT results-join + expanded B7 aliases (PR 479/480). No gate shopping; no new Lab windows from Odds densify.

## Executive grades (Test-A OOS primary)

| Pillar               | Grade     | Detail                                                                                               |
| -------------------- | --------- | ---------------------------------------------------------------------------------------------------- |
| Predictive Quality   | **AMBER** | n=2205; B2 MAE 9.2480 vs B1 8.5703 (ratio=1.0791); clears soft AMBER, not market-relative GREEN      |
| Market Edge Evidence | **AMBER** | ATS clears (0.5305 n=2200) but CLV/ROI soft (CLV+=0.5012 n_clv=1676; ROI=0.014) — no Edge>4 shopping |
| Evidence Quality     | **GREEN** | n_actual=2205; outcome_cov=95.95%; leakage=0; continuity PRIOR/UNKNOWN only; SoT D locked            |

**Subscriber Influence (recommendation to CoS → Ryan):** **INSUFFICIENT EVIDENCE**

Mixed / soft pillars — no influence claim

## Coverage n (primary report grain)

- Test-A: `n_with_actual` / `n_lab` = `2205` / `2298` (cov `0.9595`)
- Train-A (diagnostic): `n_with_actual` / `n_lab` = `3583` / `3676` (cov `0.9747`)

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

| Metric           | Value   |
| ---------------- | ------- |
| n lab games      | 2298    |
| n with actual    | 2205    |
| outcome coverage | 0.9595  |
| B2 margin MAE    | 9.248   |
| B2 margin RMSE   | 11.721  |
| B2 signed bias   | -0.0728 |
| B1 margin MAE    | 8.5703  |
| B1 margin RMSE   | 10.9214 |
| B2 MAE ≤ B1      | False   |
| B2/B1 MAE ratio  | 1.0791  |

## Test-A Market Edge (full slate; honest open CLV)

| Metric                  | Value                             |
| ----------------------- | --------------------------------- |
| filter                  | `full_slate_no_edge_gt4_shopping` |
| n ATS                   | 2200                              |
| ATS                     | 0.5305                            |
| ROI (−110)              | 0.014                             |
| n open honest w/ actual | 2205                              |
| n CLV move              | 1676                              |
| CLV+ rate               | 0.5012                            |
| mean CLV move           | 0.0624                            |

## Test-A Evidence

- Continuity: `{'PRIOR': 2298}`
- Open snapshot honest (lab rows): `2298`
- PR 477 ESPN Schedule SoT A package exists (slate_complete=false); Lab joins remain Odds event_id + B7 fail-closed for this scorecard

## Train-A diagnostic (context only — not primary grade)

| Metric           | Train-A          |
| ---------------- | ---------------- |
| n lab / n actual | 3676 / 3583      |
| B2 MAE / B1 MAE  | 9.5089 / 8.746   |
| ATS / ROI        | 0.5042 / -0.0412 |
| CLV+ (n_move)    | 0.4972 (2697)    |

## Hard NOT (held)

- Edge Board / PLAY / Conf% / props
- Odds densify / invent tips / KenPom-as-SoT / #12 GO-2 / squash
- Retune after seeing Test-A
- Shopping grade thresholds after densify
