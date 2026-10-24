# Holdout expected answers v4 — hand check (filed before the runner)

Gate table + lock/receipt fields + fold years + delta producer + B-8a
anchored PASS rule + B-13 production paths + PENDING_RYAN scorer v6.2.
**No holdout values.** `holdout_values` is null.

Filed against IMV RETURN `4fd6cfbe` + erratum `b746e5eb`. Ryan CLEAR
`fabf8732`. Real lock not written. No 2024/25 byte. Active scorer pin
`ca98ae0e`. Scorer v6.2 sha `1129354a` is **PENDING_RYAN**.

## Folds (B-3, accepted)

From request v3.1 §2 parse `season ∈ {2024, 2025}`: F1=2024, F2=2025, pooled.
Fixture stand-ins (B-2/B-7): 2098 / 2099. Never literals 2022/2023.

## Delta producer (B-4) and Path 1 composition (B-10)

`holdout_delta_producer.py` sha `43d80936`. Deltas from
`apply_params(8d188da2, selected_params from 6a5490db)` under `ff8e6527`,
pre-kickoff only, `as_of <= kickoff`. Extra player keys refused.
`QB1_INDEX_UNITS = 0.12` from fit `qb1_floor / qb1_points_per_index_unit`.
`games.json` raw deltas forbidden.

Path 1 holdout export = that producer + writer `9947b880`
`timestamps_for_game` + `write_sidecar_chain`. `writer.main()` is not
invoked on holdout.

## PASS-file rule (B-8a)

Read exact dir `/workspace/fg-repair/imv-gate1-review-2026-10-02/`
`IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_vN.txt`. Verify `.abs.sha256`
and 0444. Exactly one anchored line matching
`^VERDICT: (PASS|RETURN|PASS WITH CONDITIONS|FAIL)$` equal to
`VERDICT: PASS`, plus a dedicated `RUNNER_SHA: <64hex>` equal to
`runner_sha()`. Not a substring test. No `REQUIRED_OPENING_PASS`.
Do not read PASS from `seeded/`.

## Receipt (B-6)

`opening_permitted` / `holdout_years_opened` computed, not hardcoded.
`fold_slim` carries I-1 values, the **scorer holm list only** (no runner
`p*(9-rank+1)`), K-2. Receipt written 0444 first. RECEIPT_MANIFEST after
that 0444 receipt and not rewritten into the receipt. SUMS = MANIFEST
lines plus the MANIFEST file hash. Both MANIFEST and SUMS 0444.

## Post-lock handler (B-1)

Catches `BaseException`. On any exception after the lock: consume sidecar
+ write receipt if not already 0444. Does not rewrite 0444. Week-1
identity runs before the receipt is written.

## Production inputs (B-13)

Exact paths under `/workspace/ops/nfl_injury_audit_t4274u/`:
`games.json`, `close.csv`, `schedule.csv`, `listings/`. Pre-lock:
existence, headers, no-open size. Missing file STOPs before the lock.

## Scorer pin (B-12 / PENDING_RYAN)

Active pin remains `ca98ae0e` (dies on 2024/2025/2026). v6.2 draft
`1129354a` is for IMV diff review only. Runner switches only if
`/workspace/fg-repair/imv-gate1-review-2026-10-02/DECISION_RYAN_SCORER_V6_2.txt`
exists (0444 + `.abs.sha256` + line `AUTHORIZE: scorer v6.2` + v6.2 sha).

## Rounding (B-9, accepted)

Decimal `ROUND_HALF_UP` to 4 decimals. In-code method-vs-CSV on
`nflverse_close_le2023.csv` (`634d8e73`) vs `502110cf` at 1e-4 tolerance.
Cited case 2015 wk12 DAL-CAR total = 45.3563 exactly. Week-1 0-0:
`record_spread = -1.05`, `record_total = 44.8435`.

## Fixtures

`F-E2E` is lock → export → guards → join → score → week-1 → consumed →
receipt on synthetic 2098/2099 (B-7). Default `--mode holdout` STOPs
`O-1 opening blocked`. Production workspace checks pins then B-13 inputs
before any lock write.
