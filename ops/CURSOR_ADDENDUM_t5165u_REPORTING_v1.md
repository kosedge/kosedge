# CURSOR ADDENDUM t5165u — reporting-arithmetic completion

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR **0ac66543** · Cos ORDER **9ad857bb** · tracker **46283**.
Same draft **#701**. HARD END 02:30 EST / 07:30Z.

**No new scientific look.** Reporting-arithmetic completion on already-consumed
frozen rows. Does not invoke the one-exec runner, `--score`, or `--cos-bind`.
Does not reset / rebind / delete the claim. Does not regenerate forecasts or
change arms / cohorts / market96. Does not overwrite EXEC RECEIPT / ONE_RUN*.

## Immutable EXEC (cited, not rewritten)

| Item | Value |
| --- | --- |
| Tip | `093a51dc9d6ef4c18fb16101a02c7395ce074096` |
| Stamp | `3001dcc32f4425596727a3c0ebb4a052bc1bd37f` |
| bind_id | `4eef5d1f843bb17327d0d81d3cdae3a8d7d91917d9763691b55808c365d0caa6` **CONSUMED** |
| ONE_RUN.json | `9a72c55be94e0fc04778da22748a70b2e159c4c95e4803c41449cbb8abfc13cc` |
| RECEIPT.json | `f8da3deab88858405fc55c0af829fde53ef4a689b697cd7a773442e564355869` |

Overall mae/rmse/bias for full496 / old437 / new59 and IF−market /
candidate−market bootstraps are **cited** from that RECEIPT (path + sha256),
not recomputed as a new look. Reconstruction matched RECEIPT `mae_if`
to 1e-12.

## 1) Joined per-game rows (not persisted at EXEC)

Reporting reconstruction from frozen completed forecasts `f4b970f0` (IF copy
of `96d3aa6f`) + pinned schedule-score bytes `08533423` + split identity
`6429f859` + market∩96 `072e99e0` / `558fbfe5`.

| Artifact | sha256 |
| --- | --- |
| `data/ops/nfl-t5165u-r5-reporting/JOINED_ROWS.json` | `df24500e4366240ca6aa7d1aedab0c8415a8bea17dbfe969d6e9fac96e77a5a0` |
| join payload | `9dc82c7b1a97f049bf6fee89f475dae031ee9f6b9a1ba63296b1bdc3343198e9` |
| n | **496** · kind `reporting_reconstruction` · label `RESEARCH_CONSUMED_RETRO` |

## 2) if_q2_candidate — candidate−IF + per-season

B=10000 seed 20261101. Negative MEAN = candidate lower abs-loss than IF.
Overall mae/rmse/bias cited from EXEC RECEIPT.

| Split | n | clusters | mae_if (cited) | mae_q2 (cited) | mae_c (cited) | MEAN L_c−L_if | game 95% | week 95% | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| full496 | 496 | 33 | 11.191978 | 10.834458 | 10.852834 | −0.339144 | [−0.5532, −0.1325] | [−0.5454, −0.1400] | CI_EXCLUDES_ZERO |
| old437 | 437 | 33 | 11.363783 | 11.029384 | 11.040111 | −0.323672 | [−0.5490, −0.0976] | [−0.5373, −0.1164] | CI_EXCLUDES_ZERO |
| new59 | 59 | 18 | 9.919454 | 9.390686 | 9.465708 | −0.453746 | [−1.0024, 0.1220] | [−1.0020, 0.1434] | INCONCLUSIVE |

Per-season MAE (reporting reconstruction):

| Split / season | n | mae_if | mae_q2 | mae_candidate |
| --- | ---: | ---: | ---: | ---: |
| full496 2020 | 240 | 10.474126 | 10.435922 | 10.296127 |
| full496 2021 | 256 | 11.864964 | 11.208087 | 11.374746 |
| old437 2020 | 210 | 10.597848 | 10.533420 | 10.409178 |
| old437 2021 | 227 | 12.072358 | 11.488206 | 11.623794 |
| new59 2020 | 30 | 9.608073 | 9.753434 | 9.504765 |
| new59 2021 | 29 | 10.241573 | 9.015430 | 9.425304 |

Finite + cohort: full496/old437/new59/market96 all finite; old+new = 496;
mae_if matches EXEC RECEIPT.

## 3) market96 (same 96) — absolute + candidate−IF

| Item | Value |
| --- | --- |
| n / clusters | 96 / 32 (41 / 55) |
| reporting_class | **DESCRIPTIVE_ONLY** (n<100) · RETRO / consumed |
| mae/rmse/bias IF | 11.194598 / 14.411356 / −1.445373 |
| mae/rmse/bias Q2 | 10.654382 / 13.568487 / 0.549995 |
| mae/rmse/bias candidate | 10.663846 / 13.645577 / −0.447689 |
| MEAN L_c−L_if | −0.530752 · game [−1.1428, 0.0616] INCONCLUSIVE · week [−0.9810, 0.0804] INCONCLUSIVE |
| IF−market (cited EXEC) | 1.150327 · game CI excludes 0 |
| candidate−market (cited EXEC) | 0.619575 · game INCONCLUSIVE |

Per-season market96 MAE: 2020 n=41 IF 11.737 / Q2 11.090 / C 11.276 ·
2021 n=55 IF 10.790 / Q2 10.329 / C 10.207.

## 4) Addendum hashes

| Hash | sha256 |
| --- | --- |
| code | `e9c71a4d4304f2908ecc51628c3f2147e2bf17ab04951a8bb016af4331ad318b` |
| input | `03e72a842aba066c64723eecfba277f5f5270ac9ba47bf9b144963086453c1df` |
| join | `9dc82c7b1a97f049bf6fee89f475dae031ee9f6b9a1ba63296b1bdc3343198e9` |
| output | `b5e564df3054f7aca3c079b97041de15a40dfe9728c4bb4e2ddd337c4e9510b1` |
| REPORTING_ADDENDUM.json | `64516e39ac908d75a85ad11e305ad0100afd8e55238750b5c1fd724bb9aaf96c` |

Command: `PYTHONPATH=services/model-service python scripts/nfl/run_nfl_t5165u_r5_reporting_addendum.py`

**STOP for Alex Phase B RO (EXEC + addendum).** CERT=0. No merge.
