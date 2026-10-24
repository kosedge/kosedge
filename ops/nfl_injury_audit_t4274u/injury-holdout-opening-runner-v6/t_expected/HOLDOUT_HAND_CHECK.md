# Holdout expected answers v6 — hand check (filed before the runner)

Gate table + lock/receipt fields + fold years + pinned frozen row
builder + deposited le2023 rebuild + B-4b(P) raw-input-sha contract
+ B-4b(n) roster years + B-8a anchored PASS rule + B-13 production
paths + Ryan scorer decision `592e0bb9` + single scorer pin
`8b482cb9`. **No holdout values.** `holdout_values` is null.
`opening_runner_pass_sha` is null.

Filed against IMV RETURN `2c71e4d0`. Ryan CLEAR `fabf8732`. Ryan
scorer decision t4340s14953 / `592e0bb9`. V62_DIFF_VERDICT PASS on
`755d30a8`. Real lock not written. No 2024/25 byte. No runtime
scorer switch.

## Folds (B-3, accepted)

From request v3.1 §2 parse `season ∈ {2024, 2025}`: F1=2024, F2=2025, pooled.
Fixture stand-ins (B-2/B-7): 2098 / 2099. Never literals 2022/2023.

## L-1 scorer relabel

Active pin `8b482cb9` at `seeded/v6.2/`. Baseline `755d30a8` at
`seeded/v6.2-755d30a8/`. Deposited DIFF `seeded/v6.2/DIFF_vs_755d30a8.txt`
sha `280d9785` is the three docstring header lines. No `DRAFT` /
`PENDING_RYAN`. IMV checks docstring-only; PASS on `755d30a8` then
carries over.

## Frozen row builder (B-4b)

`holdout_frozen_row_builder.py` sha `247744d2`. Builds player `value`
and `x_continuity` with frozen `precompute_games` (`8d188da2`
`_structural_index` / `continuity_for_team`) under HEAD `8e2a15ac`
`QB1_INDEX_UNITS = 0.12` (`ebd3dac0`). Raw pins: schedule `ce80fe92`,
rosters 2012–2023, listings-le2023. `games.json` is identity-only;
value / x_continuity / deltas from it are refused.

### B-4b(R) deposited rebuild

Do not take 0-diff from this note. IMV reads:

- `out/le2023/rebuilt_le2023_deltas.json` sha `8af44a7e` — 2863 rows
- `out/le2023/rebuilt_le2023_compare.json` sha `bc89721f` — `0_DIFF`
  vs export `a38a55bb`

### B-4b(n) allowed roster years

- le2023: 2012–2023
- production: 2023, 2024, 2025
- synthetic: 2098, 2099
- 2026: never

`load_rosters_dir` STOPs on a year outside the declared set.

## B-4b(P) production raw-input shas

Lock and receipt record `raw_input_shas`: sha256 of every
`listings_*.csv`, `schedule.csv`, `roster_*.csv`, `close.csv`,
`games.json`, computed **before any data row is parsed**. Whole-file
sha256 is not a row parse. Header-only B-13 checks run after the
hash. This package has no production files and does not write
`REAL_LOCK`.

## Delta producer (B-4 / B-4c) and Path 1 composition (B-10)

`holdout_delta_producer.py` sha `ae8f9585`. Calls the builder, then
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
file hash. Both MANIFEST and SUMS 0444. Receipt repeats
`raw_input_shas`.

## Post-lock handler (B-1, accepted)

Catches `BaseException`. On any exception after the lock: consume sidecar
+ write receipt if not already 0444. Does not rewrite 0444. Week-1
identity runs before the receipt is written.

## Production inputs (B-13 + B-4b + B-4b(P))

Exact paths under `/workspace/ops/nfl_injury_audit_t4274u/`:
`listings/`, `schedule.csv` (gameday+gametime), `rosters/`, `close.csv`,
`games.json` (identity-only). Pre-lock: existence, **whole-file hash**,
headers, no-open size. Missing file STOPs before the lock.

## Scorer pin (B-14 / Ryan t4340s14953 / L-1)

Exactly one scorer sha in code: `8b482cb9` (v6.2 FINAL). Decision file
path `/workspace/ops/nfl_injury_audit_t4274u/DECISION_RYAN_SCORER_V6_2.txt`
sha `592e0bb9`. Ryan verbatim: "Yes: allow scorer v6.2 for the opening,
only if IMV passes the diff as holdout-allowance-only with no metric
change". IMV already passed that condition on `755d30a8`. No runtime
switch.

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
`O-1 opening blocked`. Production workspace checks pins then B-13
inputs before any lock write. No real lock. No opening.
