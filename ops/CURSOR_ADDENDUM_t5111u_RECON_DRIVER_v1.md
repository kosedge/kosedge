# CURSOR ADDENDUM t5111u — 2020–23 recon driver v1

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER t5111u · CoS ORDER t5111u · same #691 · authorized reconstruction successor under 32476 + t5108u
**Not a scored look. No Stage C. No 2017 outcome rescoring.**

## Preserve

| Pin                                 | Value                                                              |
| ----------------------------------- | ------------------------------------------------------------------ |
| PR                                  | https://github.com/kosedge/kosedge/pull/691 (DRAFT)                |
| Parent tip (t5110u stamp)           | `3033b4d6854ab92623a3dcf54376c43df2e280e5`                         |
| This implementation tip             | `c6d229783e8a35432c56b24835435c688233ceb9`                         |
| Design seal (not a forecast freeze) | `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd` |
| Helper pin                          | `7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64` |
| Helper source                       | #686 @ `43b5a62233b3d1d03ad2b25f5ec7dc52be29b31b`                  |
| Contract                            | `b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4` |
| Stage B full matrix                 | `cd9af2858e21fac5247a489051f0cc61b9490cb97ffdec9ac41a31a2d224d810` |
| Stage B W7–W8 slice                 | `3ab291d66a5b5da88daa073413635196e7361ffc9e1e2eafb35c652bedc7c441` |

No merge / deploy / paid Odds. No real EVAL. No helper.main / OOS / 1ee90fac.

## Helper pin proof

Vendored exact bytes of `research/q2s_w7w17_t5044u/gate2/method_7e77c57f/build_recon_t4893u.py` from #686 @ 43b5a62233.

`sha256(services/model-service/src/services/nfl_t5107u/vendor/build_recon_t4893u.py)` =
**`7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64` MATCH.**

Driver `importlib`-loads that file after the pin check. `main` and `load_oos_2016_2017` are replaced with refuse closures. Path tokens `1ee90fac` / `historical_oos_games.csv` / `historical-oos` are refused.

Imported unchanged: `t1_from_plays`, `rolling_5g`, `lookup_t2`, `rest_days_et`, `team_strength_from_record`, `record_asof`, `synthetic_t1_selfcheck`, `parse_utc`, `selection_hash`.

## New reconstruction hashes (2023 REG W2–W18)

Old b41f4b43 2017 artifact **cannot** share row hashes with these rows.

| Artifact                          | sha256                                                             | n                                       |
| --------------------------------- | ------------------------------------------------------------------ | --------------------------------------- |
| Completeness seal (before PBP)    | `b2ded70823363d1a8a002824ae4c3d32476640cbffa66814b2ada081f027401c` | 256 eligible / 16 W1 excluded           |
| Canonical matrix JSON             | `dd3593dca5fc4969197a915b69a2b000912bbd2c023972e5f666c233cd923b4a` | 6912 cells (256×27)                     |
| `RECON_MATRIX_2023_REG_W2W18.csv` | `52b5dd358f96621445eed42cdf06bf1c9f0d257dda2e0d5899f351eab0844644` | 228 complete 27/27 · 28 partial no-fill |
| Limited W2 completeness           | `3d9231cead0ba75b939293cf6826e6a0474acdb475dca90d79077ed5ce2f2958` | 16 W2 eligible                          |
| Limited W2 matrix JSON            | `44aa0ddacfde177c752fb72221c4ea5551aee43c2f71d3fc575a0dfb082a696c` | 432 cells                               |
| Limited W2 CSV                    | `129dca2192246c7ea7b0c1c97b6e15b3416db072e47adfb4af75338df9355ab2` | 15 complete · 1 partial                 |

Labels on every cell: **RECONSTRUCTED** / **RETRO_FIT** / **RESEARCH_CONSUMED_RETRO**. `cert_candidate=0`.
Archived IF mus are **not** a prerequisite on this route.

28 partials are fail-closed T2 exact `rating_week=week-1` misses or non-finite 5g (bye / 0-denominator RZ). No last-played fill. W1 (16) frozen excluded before PBP open (`W1_NO_PRIOR`).

## Provenance

| Field                                 | Source                                              | sha256 / pin            | Status             |
| ------------------------------------- | --------------------------------------------------- | ----------------------- | ------------------ |
| identity + `kickoff_utc`              | games.csv                                           | `4fe1cdd7…abef8`        | hashed             |
| `rest_days_*`                         | helper `rest_days_et` ET DOW (Thu=4, Mon=6, else=7) | `7e77c57f`              | imported           |
| `offense_index_*` / `defense_index_*` | helper `team_strength_from_record` + `record_asof`  | `50bda875` / `253e178b` | imported           |
| T1/T2 5g EPA/success/pass/pressure/RZ | helper `t1_from_plays` + `rolling_5g` + `lookup_t2` | helper + PBP `4aeca98e` | imported           |
| T4 `matchup_diff_*`                   | helper.main T4 contract applied to imported T2 rows | `7e77c57f`              | applied unchanged  |
| 2020–22 T5 W-L                        | outcomes score-only                                 | `50bda875…dc081`        | hashed             |
| 2023 T5 W-L                           | PBP score-only extract (game_id join)               | `253e178b…63da`         | hashed             |
| Stage B W7–W8 input ref (schema only) | #674 slice                                          | `3ab291d6…c441`         | hashed; no rescore |
| Stage C / 1ee90fac / old OOS          | forbidden                                           | `1ee90fac`              | FORBIDDEN          |

games.csv `rest_days_*` hardcoded 7.0 and `epa_*` columns are **not** used.

## Parity tests

```
# pandas present (kosedge .venv)
cd services/model-service && PYTHONPATH=. python -m pytest tests/test_nfl_t5111u_recon_driver.py -q
# 12 passed

# python3.11 (no pandas): prior 59 + 5 t5111u always-on; 7 helper-import tests skipped
cd services/model-service && PYTHONPATH=. python3.11 -m pytest \
  tests/test_nfl_odds_reader.py \
  tests/test_nfl_odds_comparison_harness.py \
  tests/test_nfl_forecast_builder_t5107u.py \
  tests/test_nfl_real_data_evaluator_t5107u.py \
  tests/test_nfl_t5108u_impl_correction.py \
  tests/test_nfl_t5111u_recon_driver.py -q
# 64 passed, 7 skipped
```

Counts: helper pin 1 · refuse 1ee90fac/OOS 2 · identity LV overlay 1 · `synthetic_t1_selfcheck` 7 rate checks · T5/rest goldens 6 · T4 sign goldens 6 · Stage B self-compare 756 cells / 27 fields / tolerances unchanged (index 1e-6, EPA 1e-9, rest 1e-9, exact numeric 0) · freeze-before-errors 1 · leakage refuse 1 · synthetic 27/27 packet + new row hashes 1 · bindings/tolerances 1.

Stage B used as **approved input-reference schema/contract only**. Closed 2017 outcomes were not rescored.

## Exact incompatibilities (not guessed / not loosened)

1. **`PBP_TO_CANON['LV']='OAK'` cannot transfer unchanged.** 2017-era helper remaps Raiders to OAK. 2020–23 games.csv / outcomes use LV (OAK count=0). Driver overlays identity only: `{LA:LAR, WAS:WSH}`; LV stays LV. LA→LAR and WAS→WSH transfer (PBP still emits LA/WAS).
2. **T4 diffs are not a helper export.** Driver applies helper.main / rebuild T4 contract unchanged (`h-a` / `a-h` / success mean). Not a new feature.
3. **`helper.main` / `load_oos_2016_2017` / quarantined 1ee90fac** — refused. Not opened.
4. **outcomes `50bda875` stops at 2022.** 2023 T5 uses owned PBP score-only extract `253e178b`. Path plumbing only.
5. **Old b41f4b43 2017 row hashes cannot match 2020–23 rows.** New hashes bound above.
6. **T5 `record_asof` is same-season only.** W1 is frozen excluded (0-0 refused, rating_week=0, no-fill). Transferable rule, not a formula change.

## Remaining blockers

- 2020 / 2021 / 2022 REG slates not generated this turn (driver ready; 2023 W2–W18 only)
- 28/256 2023 games partial (bye / non-finite T2; no-fill) — packets not 27/27
- Full `RECON_MATRIX_2020_2023_REG` still incomplete
- Alex GO + CoS one-run bind (procedural; not issued)
- Real EVAL still gated; design seal ≠ forecast freeze
- pandas required to import helper T1 (CI python3.11 without pandas skips those 7 tests)
- Produce-μ ready for complete 27/27 packets; archived IF mus still missing and **not** required on this route

HARD END 15:00 ET / 20:00 UTC. DRAFT only. CERT=0.
