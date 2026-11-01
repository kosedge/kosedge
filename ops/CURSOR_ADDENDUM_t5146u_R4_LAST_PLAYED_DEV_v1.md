# CURSOR ADDENDUM t5146u — R4-LAST-PLAYED-DEV freeze

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5146u **fdbd23f9** · Cos ORDER Cursor **b1153a45**
Parent tip **61436fdb** (t5116u stamp). Implementation tip **a7f53657**.
Isolated opt-in path. No EVAL EXEC.
**STOP — awaiting Alex source/selection PREFLIGHT GO + Cos EXEC release.**
No 2020–21 reconstruction artifact on this tip.

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

**Not written:** NEW DEV 2020–21 last-played reconstruction artifact.

## Tests

```
cd services/model-service && PYTHONPATH=. python -m pytest \
  tests/test_nfl_t5146u_last_played_t2.py \
  tests/test_nfl_t5111u_recon_driver.py -q
# 14 last-played + 12 exact-week driver
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
