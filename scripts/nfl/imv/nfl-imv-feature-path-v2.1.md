# IMV local feature path v2.1 — fd97f103

v2 design is **NOT APPROVED** until the builder + parity tests exist and the
prod CURRENT-ROW leak is fixed. This file is the v2.1 addendum. Parent:
`nfl-imv-feature-path-v2.md`. **Do not run the builder or W7** until IMV
code-checks these files.

Pin: `b1d857d356d5afc422c86ffb1e9a25afdf2a4225`. Injury: **ALLOWED-FLAGGED**.

## C-2 leak (why v2 path failed)

Prod `ingest.py:1313+` rolling window:

```text
ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
```

That **includes the current week**. Joining that row to the same game week is
same-week PBP leak. v2.1 **does not call that SQL as-is**.

v2.1 window:

```text
ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
```

Join rule: for game week `W`, use rolling computed at `as_of_week = W-1`.
Source weeks must satisfy `(season, week) < (2026, W)`. 2025 tail is prior.
Each feature row records `as_of` (week, source_weeks, prior_weeks_only,
pre_kickoff, status, flags). Fail → `BLOCKED_SAME_WEEK_LEAK`.

## C-1 feature-store pin

Builder writes `FEATURE_STORE.sha256` = sha256 of the canonical lines

```text
<sha256>  features.jsonl
<sha256>  feature-flags.jsonl
<sha256>  imv-local.sqlite   # if present
```

Sealed v2.1 requires `IMV_FEATURE_STORE_SHA` **or** that file. Mismatch or
missing pin → **BLOCKED**.

## C-3 builder + parity (files; do not run live)

| File                                               | Role                                                                         |
| -------------------------------------------------- | ---------------------------------------------------------------------------- |
| `nfl_imv_v21.py`                                   | as-of, injury, pin, HFA, week parse, builder, parity                         |
| `nfl-imv-feature-build-v2.1.sh`                    | S-1 BASE, sha-pinned prestage, required `--game-week-cap` / `--pbp-week-cap` |
| `services/model-service/tests/test_nfl_imv_v21.py` | synthetic parity vs prod CURRENT-ROW + week cap                              |

Caps: retro W4–W6 `game-week-cap=6` `pbp-week-cap=5`. W8 `game-week-cap=8`
`pbp-week-cap=7`. Week 7 as a **mode** is refused.

## Injury ALLOWED-FLAGGED (C-4)

Null handling is in `injury_allowed_flagged()`. Recorded per row.
`explicit_zero` is **removed**. Any numeric imputation →
`FLAG_IMPUTED_INJURY_DEFAULT` and still emitted as **null**. Raw
`injuries_2026` is never mapped into impact keys
(`FLAG_RAW_INJURIES_2026_REFUSED`). Sim kwargs stay `None`.

## Other runner conditions

- C-5 missing kickoff → `BLOCKED_MISSING_KICKOFF`, no `w8_first` fallback
- C-6 label `BLOCKED_NO_MODEL_EXECUTION`; week from `20xx-W##-`, not `gid[8:10]`
- C-7 `HOME_FIELD_POINTS` imported from BASE `calibration.py`, assert `== 1.05`
- C-8 `PYTHONDONTWRITEBYTECODE=1` `GIT_OPTIONAL_LOCKS=0`; EPERM written inside the seal

## Call rule

Unchanged: rest + EPA + lagged backbone indices + declared HFA + injury
**None**. Else nulls, `BLOCKED_NO_MODEL_EXECUTION`, still seal.
