# fd97f103 — C-1..C-8 trace (v2.1)

Ruling: runner v2 PASS WITH CONDITIONS; feature path NOT APPROVED until
builder + parity exist and the CURRENT-ROW leak is fixed. v2.1 is a \*\*diff

- files**. Builder and W7 were **not run\*\*.

| Cond                                                           | Verdict in v2                                | v2.1 fix                                                                                                             | Where                                                                                     |
| -------------------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| C-1 pin feature-store sha, BLOCK on mismatch                   | Store read, no pin                           | `feature_store_digest` + `FEATURE_STORE.sha256`; runner `assert_feature_store_pin`; missing/mismatch → BLOCKED       | `nfl_imv_v21.py` `assert_feature_store_pin`; `nfl-imv-sealed-v2.1.sh` feature-store block |
| C-2 per-row as-of (prior weeks, pre-kickoff)                   | Prod window includes current week            | Lagged window `5 PRECEDING AND 1 PRECEDING`; `record_as_of_check` on every row; same-week → `BLOCKED_SAME_WEEK_LEAK` | `nfl_imv_v21.py` `record_as_of_check` / `lagged_source_weeks`; runner row loop            |
| C-3 builder + parity + week cap                                | Design only                                  | Builder script + `build`/`parity` CLI; tests use `--week-cap` and flag prod CURRENT ROW                              | `nfl-imv-feature-build-v2.1.sh`; `test_nfl_imv_v21.py`                                    |
| C-4 remove explicit_zero                                       | `injury_source == explicit_zero` allowed 0.0 | Exception deleted. Null + flags only. Imputation flagged, still null                                                 | `injury_allowed_flagged`; runner `try_sim`                                                |
| C-5 missing kickoff → BLOCKED, no fallback                     | `kickoff or w8_first`                        | `require_kickoff`; no slate-first fallback                                                                           | runner slate loop; `require_kickoff`                                                      |
| C-6 BLOCKED_NO_MODEL_EXECUTION; week slice ~l.680              | `NOT_RUN` / `gid[8:10]` → `-A`               | `model_execution_label(False)`; `parse_product_week` on `W##`                                                        | `parse_product_week`; runner week + label                                                 |
| C-7 read HFA from pinned code, assert == 1.05                  | Hardcoded `1.05`                             | Import `HOME_FIELD_POINTS` from BASE `calibration.py`; mismatch → BLOCKED                                            | `read_and_assert_hfa`; runner before sim                                                  |
| C-8 PYTHONDONTWRITEBYTECODE, GIT_OPTIONAL_LOCKS, EPERM in seal | EPERM before FIXED_OUT                       | env exported at top; FIXED_OUT then `EPERM_PROBE.json`                                                               | `nfl-imv-sealed-v2.1.sh` header + probe                                                   |

Injury (ALLOWED-FLAGGED): `injury_allowed_flagged` records
`FLAG_MISSING_KOSEDGE_INJURY_NOWCAST` per row; `FLAG_IMPUTED_INJURY_DEFAULT`
if a number was present; `FLAG_RAW_INJURIES_2026_REFUSED` if mapped from
nflverse IR. Sim always gets `None`.
