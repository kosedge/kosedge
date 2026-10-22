# IMV local feature path v2.2 — f9b25e81

v2.1 was **PASS WITH CONDITIONS**. The blocking condition: every feature row
wrote `offense_index_*` / `defense_index_*` as **null** because §5.3 was a
comment, not a call. v2.2 implements that rebuild and the X-gating IMV
required before any Mac run.

Parent: `nfl-imv-feature-path-v2.md` + `nfl-imv-feature-path-v2.1.md`.
**Do not run the builder, sealed runner, or W7** until IMV code-checks these
files. Pin: `b1d857d356d5afc422c86ffb1e9a25afdf2a4225`. Injury:
**ALLOWED-FLAGGED**.

Allowed later: W4–W6 `RETROSPECTIVE` (`--game-week-cap 6 --pbp-week-cap 5`);
W8 `PROSPECTIVE-RESEARCH` (`--game-week-cap 8 --pbp-week-cap 7`), seal before
`2026-10-30T00:15:00Z`. W7 mode refused.

## Gating before ANY Mac run

### X-1 — external store pin, no fallback

`IMV_FEATURE_STORE_SHA` must be supplied from **outside** the store (operator
env, not `FEATURE_STORE.sha256` inside the directory). Empty →
`FEATURE_STORE_SHA_UNPINNED_EXTERNAL`. Digest mismatch →
`FEATURE_STORE_SHA_MISMATCH`. `fallback_used` is always `false`.

```bash
# sha is computed on the store, then copied OUTSIDE it, then passed back in
IMV_FEATURE_STORE_SHA=$(cat /var/tmp/operator-pins/FEATURE_STORE.sha256)
# do NOT: IMV_FEATURE_STORE_SHA=$(cat "$IMV_FEATURE_STORE/FEATURE_STORE.sha256")
```

### X-8 — builder network deny + EPERM

`nfl-imv-feature-build-v2.2.sh` is Darwin-only. First invocation re-execs
under `sandbox-exec` `(deny network*)`. After `--out` is created it probes
`1.1.1.1:443` and requires `errno.EPERM`. Result is written into `--out`
(`EPERM_PROBE.json`). Any other errno or a successful connect → exit 3.

### X-9 — refuse existing OUT; stamp helper sha

`--out` must not exist (`-e` check before mkdir). The Python builder also
returns `OUT_DIR_EXISTS` if `out_dir.exists()`. `HELPER.sha256` is the
sha256 of `nfl_imv_v22.py`.

The shell creates `--out` for the EPERM/HELPER stamps, then builds into
`--out/store` (fresh) and copies store files up.

## §5.3 strength-index rebuild (X-2)

Not warehouse true-PR. Local, lag-only, pinned BASE functions:

1. Weekly REG rates from pre-staged PBP. 2025 capped at week 18; 2026 capped
   at `pbp_week_cap` (= `game_week_cap - 1`). Postseason dropped.
2. Season rows = play-weighted averages of those weeks, `week <= as_of_week`
   for the current season (`as_of_week = game_week - 1`).
3. `build_package_from_season_row` (prior 2025 + current) →
   `blend_packages` → `prior_current_blend_weight`
   (`w_current = clamp(completed_reg/8, 0, 1)`) →
   `package_to_strength_indices`.
4. Stamp `prior_source=pbp_rolling_backbone`, `as_of_week`, `w_current_*`,
   input shas.
5. Import failure or missing 2025 prior → null indices,
   `FLAG_MISSING_TRUE_PR_PRIOR`. Never emit dataclass `1.0`.

## 5g window (X-6)

```text
last 5 completed REG team-games with (season, week) < game;
bye weeks omitted (no row); postseason omitted; 2025 REG tail fills early 2026
```

Calendar-week holes (bye) are **not** averaged as missing slots. Week > 18
and `season_type` in POST/\* playoff tags are dropped before the window.

## Cap pair (X-5)

| Target | `--game-week-cap` | `--pbp-week-cap` | Label                |
| ------ | ----------------- | ---------------- | -------------------- |
| W4–W6  | 6                 | 5                | RETROSPECTIVE        |
| W8     | 8                 | 7                | PROSPECTIVE-RESEARCH |
| W7     | 7                 | any              | **refused**          |

`pbp` must equal `game - 1`. W7 PBP as **lag for W8** is required (`pbp=7`
when `game=8`); W7 as a **mode** is refused.

## Parity (X-3)

`PARITY_KEYS` is 14 numeric keys (EPA / pressure / pass / success / rest /
diff / roof). Fewer than 3 keys → `FAIL_TOO_FEW_KEYS`. Any compared value
mismatch → `FAIL_VALUE_MISMATCH` (not PASS-with-diffs). Fixtures:
`scripts/nfl/imv/fixtures/parity-{local,prod}-w6-sample.jsonl` (W5/W6
real-shaped rows; prod `as_of_week == game week` = CURRENT ROW leak; W7
row dropped by `--week-cap 6`).

## Injury record (X-4)

`injury_row_record` wraps `injury_allowed_flagged`. `defaulted_injury` is
**derived** (`FLAG_IMPUTED_INJURY_DEFAULT` present), never hardcoded
`false`. Sim still receives `None`.

## Run label (X-7)

| Condition                                       | Label                        |
| ----------------------------------------------- | ---------------------------- |
| any null model output, or `model_calls_ok <= 0` | `BLOCKED_NO_MODEL_EXECUTION` |
| other blocked flags                             | `BLOCKED`                    |
| W4–W6 success                                   | `RETROSPECTIVE`              |
| W8 success                                      | `PROSPECTIVE-RESEARCH`       |

## Files (do not run live)

| File                                               | Role                                     |
| -------------------------------------------------- | ---------------------------------------- |
| `nfl_imv_v22.py`                                   | X-1..X-7 contracts + §5.3 builder/parity |
| `nfl-imv-feature-build-v2.2.sh`                    | X-8/X-9 Darwin builder                   |
| `nfl-imv-sealed-v2.2.sh`                           | sealed runner (imports v22)              |
| `services/model-service/tests/test_nfl_imv_v22.py` | synthetic + fixture contracts            |
| `nfl-imv-v2.2-x-trace.md`                          | this ruling's X table                    |

Call rule unchanged: rest + EPA + **rebuilt** lagged backbone indices +
declared HFA + injury **None**. Else nulls, `BLOCKED_NO_MODEL_EXECUTION`,
still seal.
