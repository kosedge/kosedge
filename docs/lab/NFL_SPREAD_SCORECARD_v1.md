# NFL Spread Scorecard v1.0

**Protocol:** `nfl-spread-validation-protocol-v1.0` (FROZEN)  
**Status:** `results_filled`  
**CoS sign-off:** Chief of Staff — 2026-09-04 — Protocol v1.0  
**Generated:** 2026-09-04T04:41:55.421044+00:00  
**Lab:** Kos Edge #3 Model Validation Lab  
**Machine JSON:** [`data/ops/lab/nfl-spread-scorecard-v1.json`](../../data/ops/lab/nfl-spread-scorecard-v1.json)

> Evidence report only. **No** live PLAY / LEAN / PASS flip recommendations.  
> RED = successful honest failure detection when criteria say so.

## Executive grades

| Pillar | Grade | Detail |
| --- | --- | --- |
| Predictive Quality | **YELLOW** | n=1693; MAE market-relative ok (model 9.5513 / market 9.7764); margin MAE=7.4801; signed bias series = N/A—DATA GAP (blocks GREEN conjunct). |
| Market Edge Evidence | **GREEN** | play_band_all ATS 0.7313 n=227; ROI 0.3961; CLV+ 0.6117 n_clv_move=206 (≥200). |
| Evidence Quality | **GREEN** | overall_n=1693; play_band n=227; CLV coverage 90.75%; contradicting regimes=0. |

**Subscriber Influence (recommendation to CoS → Ryan):** **YES**  
Predictive ≥ YELLOW; Market Edge GREEN; Evidence Quality GREEN (scoped to confirmatory PLAY-band evidence — not a live tag flip).

Primary-2025-alone Market Edge (context): `YELLOW` — ATS clears (ATS=0.6964 n=112, ROI=0.3295) but CLV soft/fails (CLV+=0.5842 n_clv_move=101; GREEN needs ≥200 @ ≥0.55).

## Data sources (owned artifacts only)

- `data/ops/nfl-play-only-holdout.json`
- `data/ops/nfl-kav-grading-after.json`
- `data/ops/nfl-kav-supervised-retrain-v3.json`
- `data/ops/nfl-enterprise-gates-latest.json`
- `data/ops/nfl-vegas-benchmark-report.json`

Citations (prior art, not Lab discovery):

- `docs/NFL_ENTERPRISE_GATES.md`
- `data/ops/nfl-play-only-holdout.json`
- `apps/web/lib/nfl-spread-play-lock.ts`
- `NFL_SPREAD_PLAY_LOCKED.md`
- `scripts/nfl/evaluate_enterprise_gates.py`
- `services/model-service/src/services/nfl_enterprise_gates.py`
- `docs/lab/NFL_SPREAD_VALIDATION_PROTOCOL_v1.md`

## Predictive Quality

| Metric | Value |
| --- | --- |
| Model spread MAE vs close | 9.5513 |
| Market spread MAE vs close | 9.7764 |
| n (all_sides) | 1693 |
| Supervised margin MAE (secondary) | 7.4801 |
| Supervised Brier (secondary) | 0.1482 |
| Signed bias (mean error) | N/A—DATA GAP |
| GREEN gate | market-relative only (no absolute-pt OR) |

## Market Edge Evidence — `play_band_all` (2.5 ≤ \|edge\| < 7.0)

| Window | n | ATS | ROI (−110) | n_clv_move | CLV+ | mean CLV move |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary unused 2025 | 112 | 0.6964 | 0.3295 | 101 | 0.5842 | 0.5693 |
| Confirmatory 2024–2025 | 227 | 0.7313 | 0.3961 | 206 | 0.6117 | 0.9684 |
| Clean-era 2020–2022 | 387 | 0.5375 | 0.0261 | 222 | 0.4505 | -0.5721 |

Full-slate ATS (context only, not selective claim): n=1693, ATS=0.4950 (enterprise full-slate gate echo: RED).

### Edge buckets (primary 2025 segments)

| Bucket | \|edge\| | n | ATS | ROI | n_clv_move | CLV+ |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `noise` | [0.0, 1.1) | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP |
| `lean_band` | [1.1, 2.5) | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP |
| `play_low` | [2.5, 3.5) | 33 | 0.5758 | 0.0992 | 28 | 0.4643 |
| `play_mid` | [3.5, 5.0) | 31 | 0.6129 | 0.1701 | 31 | 0.6452 |
| `play_high` | [5.0, 7.0) | 48 | 0.8333 | 0.5909 | 42 | 0.6190 |
| `mega_edge` | [7.0, ∞) | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP | N/A—DATA GAP |

## Regimes

| Regime | Status / metrics |
| --- | --- |
| `home_side` | n=57, ATS=0.6842, CLV+=0.6383 (n_move=47) |
| `away_side` | n=55, ATS=0.7091, CLV+=0.5370 (n_move=54) |
| `edge_play_low` | n=33, ATS=0.5758, CLV+=0.4643 (n_move=28) |
| `edge_play_mid` | n=31, ATS=0.6129, CLV+=0.6452 (n_move=31) |
| `edge_play_high` | n=48, ATS=0.8333, CLV+=0.6190 (n_move=42) |
| `favorite` | N/A—DATA GAP |
| `dog` | N/A—DATA GAP |
| `week_W1_W4` | N/A—DATA GAP |
| `week_W5_W12` | N/A—DATA GAP |
| `week_W13_W18` | N/A—DATA GAP |
| `postseason` | N/A—DATA GAP |
| `outdoor` | N/A—DATA GAP |
| `dome` | N/A—DATA GAP |

## Comparators

| Comparator | Status | Notes |
| --- | --- | --- |
| `kosedge_alone` | ok | n=227, ATS=0.7313, ROI=0.3961, CLV+=0.6117 |
| `market_alone` | N/A—DATA GAP | Home-favorite baseline ATS not present in owned ops JSON — do not invent. |
| `kosedge_plus_market` | N/A—DATA GAP | Filtered momentum-agreement slice not precomputed in holdout artifact. |

## Walk-forward by season (`play_band` spread)

| Season | n | ATS | ROI | n_clv_move | CLV+ |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 124 | 0.5484 | 0.0469 | 71 | 0.3662 |
| 2021 | 130 | 0.5308 | 0.0133 | 78 | 0.4487 |
| 2022 | 133 | 0.5338 | 0.0191 | 73 | 0.5342 |
| 2023 | 120 | 0.7000 | 0.3364 | 97 | 0.5361 |
| 2024 | 115 | 0.7652 | 0.4609 | 105 | 0.6381 |
| 2025 | 112 | 0.6964 | 0.3295 | 101 | 0.5842 |

## DATA GAPs (honest)

- Signed mean spread error (bias) not present in grading artifacts → Predictive GREEN bias conjunct = N/A—DATA GAP.
- Bucket `noise` ATS/CLV not in nfl-play-only-holdout segments → N/A—DATA GAP.
- Bucket `lean_band` ATS/CLV not in nfl-play-only-holdout segments → N/A—DATA GAP.
- Bucket `mega_edge` ATS/CLV not in nfl-play-only-holdout segments → N/A—DATA GAP.
- Secondary CLV `clv_pred_ts_to_close` (prediction-timestamp→close) not in artifacts → N/A—DATA GAP.
- Regime `favorite` field coverage <80% / absent → N/A—DATA GAP.
- Regime `dog` field coverage <80% / absent → N/A—DATA GAP.
- Regime `week_W1_W4` field coverage <80% / absent → N/A—DATA GAP.
- Regime `week_W5_W12` field coverage <80% / absent → N/A—DATA GAP.
- Regime `week_W13_W18` field coverage <80% / absent → N/A—DATA GAP.
- Regime `postseason` field coverage <80% / absent → N/A—DATA GAP.
- Regime `outdoor` field coverage <80% / absent → N/A—DATA GAP.
- Regime `dome` field coverage <80% / absent → N/A—DATA GAP.
- Comparator market_alone → N/A—DATA GAP.
- Comparator kosedge_plus_market → N/A—DATA GAP.

## Hard locks honored

- No rematerialize / no live tag flip / no invented odds / no p-hacking
- CBB excluded
- Criteria frozen at Protocol v1.0 — buckets/min-N/G-Y-R not retuned after results
- RED is a successful Lab outcome when criteria detect failure

## Re-run

```bash
python3 scripts/lab/nfl_spread_validation_v1.py
```

Requires the cited ops JSON artifacts under `data/ops/` (no DB required for this Lab pass).
