# NCAAM Lab — results-join densify (#14 CONTINUE GO)

**As of:** 2026-09-04
**Base branch:** `deploy-vercel`
**Scorecard v1:** FROZEN (no grade retune; enables v1.1 later)

## Diagnosis

Scorecard v1 joined only thin actual_margins.parquet (406 event_ids). espn_cbb_games_*.csv scrapes are sparse + short-name B7 miss rate high; SportsData parquet is 2025-only (scrambled trial margins). Schedule SoT packs already carry B7-mapped final scores for Lab tip windows.

## Coverage receipt (cited n)

| Metric | Before (event_id actual_margins) | After (Schedule SoT packs + B7) | Lift |
| ------ | -------------------------------- | ------------------------------- | ---- |
| Train-A n_lab | 1119 | 1119 | — |
| Train-A n_with_actual | 170 | 1080 | +910 |
| Train-A outcome_coverage | 0.1519 | 0.9651 | +81.32 pp |
| Test-A n_lab | 609 | 609 | — |
| Test-A n_with_actual | 80 | 566 | +486 |
| Test-A outcome_coverage | 0.1314 | 0.9294 | +79.8 pp |

## Join policy

- Lab schedule SoT remains **D** (Odds `event_id` + B7)
- Results primary: Schedule SoT packs on `tip_date` + `home_team_id`/`away_team_id`
- Results secondary: owned `actual_margins.parquet` / `results.csv` by `event_id`
- Fail-closed: unresolved B7 / ambiguous keys → omit; never invent margins
- **No Odds API densify / credit burn**

## Leakage / continuity

- KenPom leakage OK: `True`
- KenPom leakage violations: `0` (must be 0)
- SETTLED forbidden total: `0` (must be 0)
- Continuity Train-A: `{'PRIOR': 1119}`
- Continuity Test-A: `{'PRIOR': 609}`

## Artifacts verified

- `schedule_packs`: primary densify — join tip_date + team_id
- `actual_margins.parquet`: secondary event_id overlay only
- `results.csv`: secondary event_id overlay only
- `espn_cbb_games_*.csv`: insufficient alone (sparse + alias gaps)
- `all_sportsdata_results_2016-2025.parquet`: 2025 season only; not Train/Test-A

## Hard NOT (held)

- Odds densify / credit burn
- Edge Board / PLAY / Conf% / props
- Invent tips / fake SETTLED / KenPom-as-SoT / #12 GO-2
- Peek-tuning of v1 scorecard grade gates or rewriting frozen v1 numbers

## How to re-run

```bash
python3 apps/web/scripts/lab_ncaam_results_coverage_receipt.py
```

Scorecard path uses densify by default (`densify_results=True`) for future v1.1;
reproduce thin v1 baseline with `build_scorecard(densify_results=False)`.
