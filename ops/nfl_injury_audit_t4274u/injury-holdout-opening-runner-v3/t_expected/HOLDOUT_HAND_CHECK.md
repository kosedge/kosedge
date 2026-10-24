# Holdout expected answers v3 — hand check (filed before the runner)

Gate table + lock/receipt fields + fold years + delta producer + PASS-file
rule + rounding. **No holdout values.** `holdout_values` is null.

Filed against IMV RETURN `77d9c00a`. Real lock not written. No 2024/25 byte.

## Folds (B-3)

From request v3.1 §2 parse `season ∈ {2024, 2025}`: F1=2024, F2=2025, pooled.
Fixture stand-ins (B-2/B-7): 2098 / 2099. Never literals 2022/2023.

## Delta producer (B-4) and Path 1 composition (B-10)

`holdout_delta_producer.py` sha `57df9a50`. Deltas from
`apply_params(8d188da2, selected_params from 6a5490db)` under `ff8e6527`,
pre-kickoff only. `games.json` raw deltas forbidden.

Path 1 holdout export = that producer + writer `9947b880`
`timestamps_for_game` + `write_sidecar_chain`. `writer.main()` is not
invoked on holdout.

## PASS-file rule (B-8)

Read exact dir `/workspace/fg-repair/imv-gate1-review-2026-10-02/`
`IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_vN.txt`. Verify `.abs.sha256`
and 0444. Text must contain `VERDICT: PASS` and this runner's
`runner_sha()`. No `REQUIRED_OPENING_PASS` constant. Do not read PASS from
`seeded/`.

## Receipt (B-6)

`opening_permitted` / `holdout_years_opened` computed, not hardcoded.
`fold_slim` carries I-1 values, 9 Holm-adjusted p-values, K-2 (Brier, LL,
reliability bins). Receipt 0444. Top-level runner/scorer sha. Receipt
MANIFEST/SUMS for opening outputs.

## Rounding (B-9)

Decimal `ROUND_HALF_UP` to 4 decimals. In-code method-vs-CSV on
`nflverse_close_le2023.csv` (`634d8e73`) vs `502110cf` at 1e-4 tolerance.
Cited case 2015 wk12 DAL-CAR total = 45.3563 exactly. Week-1 0-0:
`record_spread = -1.05`, `record_total = 44.8435`.

## Fixtures

`F-E2E` is lock → export → guards → join → score → receipt on synthetic
2098/2099 (B-7). Default `--mode holdout` STOPs `O-1 opening blocked`.
Production workspace goes through `run_holdout_workspace` (pins first).
