# f9b25e81 — X-1..X-9 trace (v2.2)

Ruling: v2.1 PASS WITH CONDITIONS. Headline: builder wrote
`offense_index_*` / `defense_index_*` **null on every row**
(`nfl_imv_v21.py` ~l.815–818) because §5.3 prior-strength rebuild was never
implemented, so every row sealed `BLOCKED_NO_MODEL_EXECUTION`.

C-2 **CLOSED** (lagged window + per-row as-of). C-1 / C-3 / C-6 **PARTIAL**
in v2.1; X-1 / X-3 / X-7 close those gaps in files. v2.2 is a **diff +
files**. Builder, sealed runner, and W7 were **not run**.

Allowed later (after IMV code-check): W4–W6 **RETROSPECTIVE**, W8
**PROSPECTIVE-RESEARCH** sealed before `2026-10-30T00:15:00Z`
(2026-10-29 20:15 ET). Pin `b1d857d3`. W7 refused.

## Gating (needed before ANY Mac run)

| Cond                                                                                           | v2.1                                                                | v2.2                                                                                                                                   | Where                                                                                |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| X-1 expected store sha supplied from **OUTSIDE** the store; no `FEATURE_STORE.sha256` fallback | File-pin fallback (`assert_feature_store_pin` used in-store digest) | Empty `IMV_FEATURE_STORE_SHA` → `FEATURE_STORE_SHA_UNPINNED_EXTERNAL`, `fallback_used=false`. Mismatch → `FEATURE_STORE_SHA_MISMATCH`. | `nfl_imv_v22.assert_feature_store_pin`; `nfl-imv-sealed-v2.2.sh` feature-store block |
| X-8 builder under network deny with EPERM probe                                                | Darwin deny on **runner** only                                      | Builder re-execs under `sandbox-exec` `(deny network*)`; probe writes `EPERM_PROBE.json` / `.txt` inside `--out`; non-EPERM → exit 3   | `nfl-imv-feature-build-v2.2.sh`                                                      |
| X-9 builder refuses an existing output dir and stamps helper sha                               | `mkdir -p` over `--out`                                             | Existing `--out` → `FAIL: X-9`; Python `OUT_DIR_EXISTS`; `HELPER.sha256` stamped                                                       | builder shell + `build_feature_store`                                                |

## Model evidence

| Cond                                                                                    | v2.1                                                                     | v2.2                                                                                                                                                                                                                 | Where                                                                            |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| X-2 implement §5.3 strength-index rebuild (lag-only, pinned source)                     | Hardcoded `None` + `FLAG_MISSING_TRUE_PR_PRIOR`                          | BASE `efficiency_backbone.build_package_from_season_row` + `blend_packages` + `prior_current_blend_weight` + `package_to_strength_indices`. `prior_source=pbp_rolling_backbone`. Miss → null, never dataclass `1.0`. | `rebuild_strength_indices`; builder writes `offense_index_*` / `defense_index_*` |
| X-3 real parity vs prod features (more than 2 keys, real data, FAILS on value mismatch) | 2-key synthetic; PASS despite diffs                                      | `PARITY_KEYS` = 14; committed W5/W6 fixtures; `<3` keys → `FAIL_TOO_FEW_KEYS`; any numeric diff → `FAIL_VALUE_MISMATCH`                                                                                              | `parity_vs_prod`; `fixtures/parity-*-w6-sample.jsonl`; `test_nfl_imv_v22.py`     |
| X-4 per-row injury null-handling record (stop hard-coding `defaulted_injury=false`)     | Runner wrote `defaulted_injury: False`                                   | `injury_row_record` derives `defaulted_injury` from `FLAG_IMPUTED_INJURY_DEFAULT`; stored on every feature + seal row                                                                                                | `injury_row_record`; runner row loop                                             |
| X-5 enforce cap pair                                                                    | No-op `if pbp >= game: pass`                                             | `pbp_week_cap == game_week_cap - 1`; allowed game caps `{4,5,6,8}`; `g==7` → `W7_REFUSED`                                                                                                                            | `enforce_cap_pair`; builder CLI                                                  |
| X-6 define 5g window across bye/postseason                                              | Calendar `lagged_source_weeks` (bye counted as a hole, POST not defined) | Last 5 **played REG** team-games with `(season,week) < game`; bye omitted (no row); POST / `week>18` dropped; 2025 REG tail fills early 2026                                                                         | `last_n_played_reg`; `weekly_situational_reg`; `WINDOW_5G_RULE`                  |
| X-7 lag-only test + correct run label                                                   | Generic `BLOCKED` / `model_execution_label`                              | Lag excludes current week; labels `BLOCKED_NO_MODEL_EXECUTION` / `RETROSPECTIVE` / `PROSPECTIVE-RESEARCH`                                                                                                            | `run_label`; `attach_lagged_rolling_played`; runner `label=`                     |

## Carry-forward (unchanged)

C-2 lagged `ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING` + `record_as_of_check`.
C-4 `explicit_zero` removed. C-5 no `w8_first` kickoff fallback. C-7 HFA from
BASE `== 1.05`. C-8 env + EPERM inside the **seal**.
