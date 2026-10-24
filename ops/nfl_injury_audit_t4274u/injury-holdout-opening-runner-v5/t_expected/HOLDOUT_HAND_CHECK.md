# Holdout expected answers v5 — hand check (filed before the runner)

Gate table + lock/receipt fields + fold years + pinned frozen row builder
+ raw-input pins + B-8a anchored PASS rule + B-13 production paths +
Ryan scorer decision `592e0bb9` + single scorer pin `755d30a8`.
**No holdout values.** `holdout_values` is null.

Filed against IMV RETURN `0505e492`. Ryan CLEAR `fabf8732`. Ryan scorer
decision t4340s14953 / `592e0bb9`. Real lock not written. No 2024/25 byte.
No runtime scorer switch.

## Folds (B-3, accepted)

From request v3.1 §2 parse `season ∈ {2024, 2025}`: F1=2024, F2=2025, pooled.
Fixture stand-ins (B-2/B-7): 2098 / 2099. Never literals 2022/2023.

## Frozen row builder (B-4b)

`holdout_frozen_row_builder.py` sha `aa9d512b`. Builds player `value` and
`x_continuity` with frozen `precompute_games` (`8d188da2`
`_structural_index` / `continuity_for_team`) under HEAD `8e2a15ac`
`QB1_INDEX_UNITS = 0.12` (`ebd3dac0`). Raw pins: schedule `ce80fe92`,
rosters 2012–2023, listings-le2023. `games.json` is identity-only;
value / x_continuity / deltas from it are refused. le2023 rebuilt
deltas match export `a38a55bb` field-wise (IMV reads outputs).

## Delta producer (B-4 / B-4c) and Path 1 composition (B-10)

`holdout_delta_producer.py` sha `6409dcb8`. Calls the builder, then
`apply_params(8d188da2, selected_params from 6a5490db)` under `ff8e6527`.
A timestamp with no zone **STOP**s (B-4c). Extra games.json values
refused. `writer.main()` is not invoked on holdout.

## PASS-file rule (B-8a, accepted)

Read exact dir `/workspace/fg-repair/imv-gate1-review-2026-10-02/`
`IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_vN.txt`. Verify `.abs.sha256`
and 0444. Exactly one anchored line matching
`^VERDICT: (PASS|RETURN|PASS WITH CONDITIONS|FAIL)$` equal to
`VERDICT: PASS`, plus a dedicated `RUNNER_SHA: <64hex>` equal to
`runner_sha()`. Not a substring test. No `REQUIRED_OPENING_PASS`.
Do not read PASS from `seeded/`.

## Receipt (B-6 / B-15)

`opening_permitted` / `holdout_years_opened` computed, not hardcoded.
`fold_slim` carries I-1 values, the **scorer holm list only** (field
renamed `i3_holm_scorer`; no runner `p*(9-rank+1)`), K-2. Receipt
written 0444 first. RECEIPT_MANIFEST after that 0444 receipt and not
rewritten into the receipt. SUMS = MANIFEST lines plus the MANIFEST
file hash. Both MANIFEST and SUMS 0444.

## Post-lock handler (B-1, accepted)

Catches `BaseException`. On any exception after the lock: consume sidecar
+ write receipt if not already 0444. Does not rewrite 0444. Week-1
identity runs before the receipt is written.

## Production inputs (B-13 + B-4b)

Exact paths under `/workspace/ops/nfl_injury_audit_t4274u/`:
`listings/`, `schedule.csv` (gameday+gametime), `rosters/`, `close.csv`,
`games.json` (identity-only). Pre-lock: existence, headers, no-open size.
Missing file STOPs before the lock.

## Scorer pin (B-14 / Ryan t4340s14953)

Exactly one scorer sha in code: `755d30a8` (v6.2 + S-2 L1663 wording).
Decision file path
`/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt`
sha `592e0bb9`. Ryan verbatim: "Yes: allow scorer v6.2 for the opening,
only if IMV passes the diff as holdout-allowance-only with no metric
change". Prior draft sha `1129354a` changed by S-2 wording only; **IMV
must re-check the 755d30a8 vs ca98ae0e diff**. No runtime switch.

## QB1 0.12 source

First-hand: `seeded/injury_paths_8e2a15ac.py` sha `ebd3dac0` (HEAD
`8e2a15ac`):
`QB1_INDEX_UNITS = 0.12`
`QB1_POINTS_PER_INDEX_UNIT = 12.5`
`QB1_FLOOR_SPREAD_POINTS = QB1_INDEX_UNITS * QB1_POINTS_PER_INDEX_UNIT`
Comment: "QB1 out = 0.12 index units × 12.5 pts/unit = 1.5 (D-2 a-priori
floor). Not a fit coefficient."

## Rounding (B-9, accepted)

Decimal `ROUND_HALF_UP` to 4 decimals. Cited case 2015 wk12 DAL-CAR
total = 45.3563 exactly. Week-1 0-0: `record_spread = -1.05`,
`record_total = 44.8435`.

## Fixtures

`F-E2E` is lock → export → guards → join → score → week-1 → consumed →
receipt on synthetic 2098/2099 (B-7). Default `--mode holdout` STOPs
`O-1 opening blocked`. Production workspace checks pins then B-13 inputs
before any lock write. No real lock. No opening.
