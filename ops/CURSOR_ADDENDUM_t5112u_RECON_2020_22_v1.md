# CURSOR ADDENDUM t5112u — 2020–22 recon + 2020–23 produce-μ / forecast freeze

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: Alex RETURN **7e888509** · CLEAR 61906c87 G2 · OWNER a498c092 · same #691
**Not a scored look. No Stage C. No 1ee90fac. No outcome join.**

## Preserve

| Pin                       | Value                                                              |
| ------------------------- | ------------------------------------------------------------------ |
| PR                        | https://github.com/kosedge/kosedge/pull/691 (DRAFT)                |
| Parent tip (t5111u stamp) | `3f0675bddfdfbdc246a19e2530ec02f34eba66e1`                         |
| This implementation tip   | `THIS_TIP`                                                         |
| Alex RETURN               | `7e88850996588a3467c234e74f74cce994c56bd77837a56b0ebb2921888d5220` |
| Helper pin                | `7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64` |
| Design seal               | `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd` |

Design seal is **not** a forecast freeze. New forecast/cohort hashes are below.

## Per-season reconstruction (same helpers / no-fill / RETRO labels)

Completeness seals frozen **before** PBP/errors.

| Season | Split | Eligible / excl. | Complete 27/27 | Partial | Completeness body | Matrix JSON     | CSV file        |
| ------ | ----- | ---------------- | -------------- | ------- | ----------------- | --------------- | --------------- |
| 2020   | DEV   | 246 / 16         | 216            | 30      | `56260441…8be0`   | `f4d99111…b5ce` | `8615a938…67f2` |
| 2021   | DEV   | 256 / 16         | 227            | 29      | `8a5cffd0…25c6`   | `0448f29d…741c` | `d51b3b1b…06e0` |
| 2022   | EVAL  | 253 / 18         | 221            | 32      | `6d2c51c4…f425`   | `7a681635…7ab0` | `4d5266ab…f784` |
| 2023   | EVAL  | 256 / 16         | 228            | 28      | `b2ded708…401c`   | `dd3593dc…3b4a` | `52b5dd35…4644` |

2022 excluded 18 = 16 W1 no-prior + **2 T5 0-0** (same-season completed games that are ties only). Helper `team_strength_from_record("0-0")` refuses; driver now freezes those out before PBP (no-fill, not loosened).

Partials remain fail-closed T2 exact `rating_week=week-1` / non-finite 5g. No last-played fill.

Binding table: `data/ops/nfl-forecast-builder-t5107u/recon/RECON_BINDINGS_2020_2023.json`

## produce-μ + forecast freeze (research-only)

Complete 27/27 packets only. Frozen IF tree 6ca03716. Q2 transfer 2013–16. `eval`/`scoring`/`look` = null.

| Pin               | sha256                                                             |
| ----------------- | ------------------------------------------------------------------ |
| produced μ map    | `6f9f467aa33e414ac724393e69416397665249400843f237828fd439dcf5c97a` |
| forecast_sha256   | `f326a39aeaf4bc43b139f2441fab3c07c2d4e6d5bb363ecea421010d5983a458` |
| cohort_sha256     | `af129383acdad81316897cea6a1d5b48ca51647b3fc51092b55b29ca284908bc` |
| forecasts payload | `376ffd66b49fe76b24b5d2450288afc55b1daf19b095ea909c843478fce7496b` |
| freeze file       | `9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732` |

`n_forecasts=892` · IF arm reconstructed=892 / blocked=0 / archived=0.  
File: `data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json`  
Sealed before outcome join. **No real EVAL.**

## Exact incompatibilities

1. Helper T5 `0-0` refuse cannot transfer as a derived index. 2022: two W2+ games with tie-only as-of records frozen excluded (`T5_ZERO_COMPLETED_SAME_SEASON`). Not guessed.
2. Prior identity/path items from t5111u unchanged (LV overlay; T4 applied-unchanged; 50bda875 ends 2022).

## Remaining blockers

- 119 partial packets (bye / non-finite T2) across 2020–23 — not in the 892 freeze
- Alex re-preflight GO + CoS one-run bind (t5113u atomic claim is a separate prerequisite)
- G5 30% per-season HOLD not applied (no score)
- CERT=0 DRAFT≠merge

HARD END soft for this authorized finish. No new experiment.
