# Provenance outputs — every claim → a deposited file

IMV `2c71e4d0`: no unevidenced claims. Each claim names the file
IMV can `sha256sum`.

## L-1 docstring-only relabel

Claim: `8b482cb9` is `755d30a8` plus the docstring header.

- Baseline: `seeded/v6.2-755d30a8/run_injury_residual_evaluator.py`
  sha `755d30a8ce0dde7cd31b2e5ded9d4e06240e73f963b68a6ae4bd9af30d90ea5f`
- Final: `seeded/v6.2/run_injury_residual_evaluator.py`
  sha `8b482cb9ddf46ea3bfb80cbfc429978467cbccc126fb0d9d7ca8013ef2f34b37`
- Diff: `seeded/v6.2/DIFF_vs_755d30a8.txt`
  sha `280d9785ffc1a313e9415e0b3cf8f75f7d0156908aba29a9902e4bb8a8788c55`
- Draft dir `seeded/v6.2-draft/` is absent.

## B-4b(R) le2023 rebuild 0-diff

Claim: rebuilt per-game `delta_margin` / `delta_total` match export
`a38a55bb` for all 2863 games.

- Deltas: `out/le2023/rebuilt_le2023_deltas.json`
  sha `8af44a7eaa96ff695e10a61c827f942020c534f578ee36893701409857429394`
  (`n=2863`, fields `game_id,season,week,home,away,delta_margin,delta_total`)
- Compare: `out/le2023/rebuilt_le2023_compare.json`
  sha `bc89721f170be3c5b4435c70597565e515d52fd662eb522516c35e1087be7501`
  (`verdict=0_DIFF`, `n_delta_margin_diff=0`, `n_delta_total_diff=0`,
  `n_missing=0`, `export_sha=a38a55bb…`, first `2013_10_BUF_PIT`,
  last `2023_9_WAS_NE`)
- Export pin: `seeded/sealed_injury_export_ts_v1.json` sha `a38a55bb…`

## B-4b(P) production raw-input shas

Claim: lock and receipt record sha256 of every production raw input
before any row is parsed. Evidence is the runner contract in
expected answers (`production_raw_input_shas`) plus the
lock/receipt `raw_input_shas` object written at runtime. This
package does not write `REAL_LOCK` and has no production listings /
schedule / rosters / close / games.json. Fixture E2E deposits
`out/synthetic/receipt.json` with the fixture raw shas.

## B-4b(n) allowed roster years

Claim: declared in `t_expected/HOLDOUT_EXPECTED.json`
`allowed_roster_years` (sha `0c31243d…`). Enforced by
`holdout_frozen_row_builder.py` sha `247744d2`.

## V62 content PASS

Claim: IMV already passed the `755d30a8` vs `ca98ae0e` content.
Evidence: ruling `seeded/IMV_RULING_NFL_INJURY_HOLDOUT_OPENING_RUNNER_v5.txt`
sha `2c71e4d0…`, line `V62_DIFF_VERDICT: PASS (holdout-allowance-only, no metric change)`.
