# CURSOR ADDENDUM t5146u — R4-LAST-PLAYED-DEV freeze

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5146u **fdbd23f9** · Cos ORDER Cursor **b1153a45**
Parent tip **61436fdb** (t5116u stamp). Implementation tip **a7f53657**.
EXEC tip **6aed4d10**.
Isolated opt-in path. Alex PREFLIGHT GO **686ce4dc** accepted.
Cos EXEC RELEASE honored — **one** NEW DEV 2020–21 last-played reconstruction.
**STOP — awaiting Alex Phase B RO.** CERT=0. No EVAL.

## STEP 0 — existing check

No accepted equivalent last-played / most-recent-prior-week T2 path.

| Evidence | Result |
| -------- | ------ |
| `recon_driver.py` @ 61436fdb | `lookup_t2(team, target_week-1)` only; notes **no last-played fill** |
| Helper `lookup_t2` @ 7e77c57f | exact `(team, week)` match; non-unique → SystemExit |
| `RECON_SUMMARY_2021_REG_W2W18.json` | 29/256 partial; reason only `T2 exact rating_week miss or non-finite` |
| R2 / R3 / Export KEI tips | no last-played T2 selector (R3 STOP retained; Export KEI distinct) |

Do **not** assume the 29 partials are all bye cases. Summary payload has no
per-side rating week, bye flag, nonfinite metric, or consumed game IDs.

## What this is

Isolated opt-in research selector: each team's most recent **same-season** T2
snapshot with `rating_week < target_week`. Home and away independent.
Original T1/T2 trailing-five-played-games, T4, rest, and index formulas are
imported, not rewritten. No new scoring or tuning.

W1 / no same-season prior remains refused. Newest nonfinite row is kept
(no skip to an older finite snapshot). Conflicting or ambiguous duplicates
refuse. Consumed identities must be unambiguous, strictly earlier than
target KO−60, exclude the target, and stay in chronological prior-game
order.

Labels: **RECONSTRUCTED** / **RETRO_FIT**. Publication and observation
timestamps **unverified**. Explicitly **not** a production-causal or
real-time source-availability claim.

## Preserve (byte-immutable — unchanged)

| Artifact | sha256 |
| -------- | ------ |
| Implementation tip | `a7f53657e1c4ec34c63a4ad91712d0cd007d8b57` |
| EXEC tip | `6aed4d100d785388b70e8022dc7b69fea17c392a` |
| Helper `build_recon_t4893u.py` | `7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64` |
| `recon_driver.py` exact-week path | `be5aa097f99c47c075d474e199f13fca2980fd282a59a69425549a9ed12e2aa5` |
| `recon_contract.py` | `a04295023db74dbd8d582ea2734e3205476f4c2b610d0223fef4a6f06ebed775` |
| 2021 REG W2–W18 summary | `f06c8b90c3a18b75710f077a0a17209bc379e371a121f511a63266a82bc335a3` |

Frozen matrices / forecasts, R2 records, and R3 STOP were not rewritten.
R2-C / G5 retained. No EVAL / 2017 scoring. No 2022–26 regen. No R2
coverage rebind.

## Isolated freeze package

`data/ops/nfl-t5146u-r4-last-played-dev/`

| File | sha256 |
| ---- | ------ |
| `SPEC.json` | `ddc71dce256fda5bbbc61a56bca56f7c3282cd1b8eb5d05c2ba76d7923a95258` |
| `SOURCE_PINS.json` | `5c8adab753e62f417e6b54f8d1996565f75369a1246ca925de91c93f7a878429` |
| `IDENTITY_MANIFEST.json` | `a82c57caf4a474a90ccc5d51414507013fba897ef21c01e92e3c455c3aa42d07` |
| `STOP_AWAITING_ALEX_PREFLIGHT_GO.json` | `4f43fdb98aa74ef5a26f05e8355b1fef7ed33f88b7a1388847d7c0e2df0fb461` |
| `FREEZE_MANIFEST.json` | `b1cf738c265c6b2d2fa0990c318c1e7e8959d887d349fa1b6972cb872591737f` |

Code sha `last_played_t2.py` =
`a6b759a52d28db2ff904bbb20d1fd2b27fa7413ec8a50c8eafcf56c403a37ce0`.

Freeze selector `last_played_t2.py` remains `a6b759a5…` (unchanged by EXEC).

## ONE EXEC (Alex GO 686ce4dc)

Exact command run once:

```
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_last_played_recon_t5146u.py --go 686ce4dc
```

DEV-only 2020–21 REG W2–W18. T1/T2 built **per season** (helper `rolling_5g` is team-only; concatenating seasons would leak 2020 into 2021 5g — refused). Target scores are not written. No error join. No forecast/market fields.

| Result | Value |
| ------ | ----- |
| n_targets | 502 |
| n_complete_27 | **502** |
| n_partial | 0 |
| n_refused | 0 |
| no-bye T4 vs frozen exact-week 2020 | 216 games / 3456 cells / 0 mismatch **PASS** |
| no-bye T4 vs frozen exact-week 2021 | 227 games / 3632 cells / 0 mismatch **PASS** |
| t1= last-five identities | **502/502** sides (`t1=<id>\|…`) |
| 2021 previous 29 partials now complete | **29 / 0 still refused** |

### Source lineage (named pins)

| Source | sha256 |
| ------ | ------ |
| games.csv identity | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` |
| outcomes 50bda875 prior-only (not in artifact) | `50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081` |
| PBP 2020 | `a7700b519197ec563aabf24ce7791896d8803f67cb73a45fcad0e8ae7db7245f` |
| PBP 2021 | `35f5d0b49905daa7d63ace9710346c48c7eb32ce0b8686629491954308013354` |
| helper 7e77c57f | `7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64` |
| exact-week `recon_driver.py` | `be5aa097f99c47c075d474e199f13fca2980fd282a59a69425549a9ed12e2aa5` |
| last-played selector (freeze) | `a6b759a52d28db2ff904bbb20d1fd2b27fa7413ec8a50c8eafcf56c403a37ce0` |
| `last_played_recon.py` | `0358487a191963deef2cd3e61c8eb7d6ed9ba3c85e5f1febb3a22c0e5bb6ac1f` |

### EXEC artifact hashes

| File | sha256 |
| ---- | ------ |
| `DEV_RECON_LAST_PLAYED_2020_2021.json` | `e2f3fab5255430aa31232c7aa3b88e9001461595ef79a00fb3f1e505e51e23b9` |
| `DEV_RECON_LAST_PLAYED_2020_2021_MATRIX.csv` | `4255f847281a73d1d5e719ca4f4354a675c4e8c82161d0192a49cd4510fe34a9` |
| `DEV_RECON_2021_PREVIOUSLY_PARTIAL.json` | `07786dddd3943cdb7f4e9859ac75483be4bd74a7b6f41e14184976ef5fc96cfe` |
| `NO_BYE_EXACT_WEEK_COMPARE.json` | `0596f5d81b31412528238f8561edcf49ed7a30701356b8265c28a402ae11f6a2` |
| `EXEC_RESULT_t5146u.json` | `500233c82b457eaa67b2e52b0cdb4a76428c424fe50e3fdb0c4146bd638a329c` |
| matrix payload | `4dd5e7e5f2791b56dcd9af72be2b1a59c69eb0ffff29c0a69084a868aeff02e8` |
| identities payload | `9522b2778def6b8f6415e71a59057eb493312ebd4c6e4ec38b120115399d3eea` |

Labels: **RECONSTRUCTED** / **RETRO_FIT**. Publication/observation timestamps **unverified**. Not production-causal.

### 2021 previously-partial 29 — all now complete

Exact-week reason was only `T2 exact rating_week miss or non-finite`. Last-played selected weeks (home / away) and `t1=` last-five IDs are in `DEV_RECON_2021_PREVIOUSLY_PARTIAL.json`. None remain refused. Selected rating weeks are not `target_week-1` on at least one side for 26/29; three are both sides same last-played week (`DAL_MIN` 6/6, `TB_WAS` 8/8, `NE_IND` 13/13). This is **post-EXEC evidence**, not a pre-run bye assumption.

| game_id | H | A |
| ------- | - | - |
| 2021_07_ATL_MIA | 6 | 5 |
| 2021_07_IND_SF | 5 | 6 |
| 2021_07_NYJ_NE | 6 | 5 |
| 2021_07_NO_SEA | 6 | 5 |
| 2021_08_DAL_MIN | 6 | 6 |
| 2021_08_JAX_SEA | 7 | 6 |
| 2021_08_MIA_BUF | 6 | 7 |
| 2021_08_NE_LAC | 6 | 7 |
| 2021_08_PIT_CLE | 7 | 6 |
| 2021_09_LV_NYG | 8 | 7 |
| 2021_09_MIN_BAL | 7 | 8 |
| 2021_10_DET_PIT | 9 | 8 |
| 2021_10_SEA_GB | 9 | 8 |
| 2021_10_TB_WAS | 8 | 8 |
| 2021_11_BAL_CHI | 9 | 10 |
| 2021_11_CIN_LV | 10 | 9 |
| 2021_11_HOU_TEN | 10 | 9 |
| 2021_11_NYG_TB | 10 | 9 |
| 2021_12_LAC_DEN | 10 | 11 |
| 2021_12_LA_GB | 11 | 10 |
| 2021_13_ARI_CHI | 12 | 11 |
| 2021_13_DEN_KC | 11 | 12 |
| 2021_14_ATL_CAR | 12 | 13 |
| 2021_14_BAL_CLE | 12 | 13 |
| 2021_14_CHI_GB | 12 | 13 |
| 2021_14_JAX_TEN | 12 | 13 |
| 2021_15_NE_IND | 13 | 13 |
| 2021_15_NYJ_MIA | 13 | 14 |
| 2021_15_WAS_PHI | 13 | 14 |

Example lineage `2021_07_ATL_MIA`: `t1=2021_02_BUF_MIA\|…\|2021_06_MIA_JAX` (home MIA W6) and `t1=2021_01_PHI_ATL\|…\|2021_05_NYJ_ATL` (away ATL W5).

## Tests

```
cd services/model-service && PYTHONPATH=. python -m pytest \
  tests/test_nfl_t5146u_last_played_t2.py \
  tests/test_nfl_t5146u_last_played_recon.py \
  tests/test_nfl_t5111u_recon_driver.py -q
# 14 last-played + 1 t1= + 12 exact-week driver
```

Covered identities (not status-only): ordinary no-bye matches exact-week
and frozen reconstruct_slate T4; one/multiple byes; distinct home/away
rating weeks; W1 / no history refuse; cross-season refuse (and ignore
other-season when a same-season row exists); duplicate conflict /
ambiguous duplicate refuse; nonfinite newest not skipped; target/future
exclusion + KO−60 boundary; target outcome change does not change
allowed features; last-five source-game identities proven.

## Holds

R2-C / G5 retained. R3 STOP 81b6c0fc. No merge / deploy / runtime-config /
paid Odds / model network / DB secrets / protected opening.
**STOP for Alex Phase B RO.** No further reconstruction on this tip.
