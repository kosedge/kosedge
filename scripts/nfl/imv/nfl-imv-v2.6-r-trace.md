# 04fd87a1 — v2.6 reader R-1 close + runbook v2.4.2

IMV v2.5 filing sha `04fd87a1`. Reader and runbook were RETURNED.
Register `39561f48` PASSES (D-1, D-2). Frozen: v21–v25 and every
other existing file. New helper: `nfl_imv_v26.py`.
Builder / seal / W7 / parity evidence were **not run**.

| ID | Ask | v2.6 |
| --- | --- | --- |
| R-1 | 41 cols = SQL v3 lines 60–102 | `PINNED_V3_COLUMNS` is that tuple. Restored `game_date`, `feature_updated_at`, `schedule_game_type`, `schedule_roof`, `schedule_updated_at`, `feature_as_of_max_utc`, `schedule_as_of_max_utc`. Removed five extra `diff_*`, `diff_rest_days`, `surface_turf`. |
| R-2 | Types for all 41 | int / date / str / bool t/f / float / ISO-UTC timestamp. Bad cell → NOT_RUN. |
| EXPORT.sha256 | Mandatory | Missing file → `EXPORT_SHA256_FILE_REQUIRED`. |
| N-1 | Concrete pre-stage | Runbook uses the script's stamped dir via `readlink LATEST`; pbp + manifest commands written. Same for W8. |
| N-2 | Anchor SUMS | `SHA256SUMS` digest must be `b0cf91da…`. No `--ignore-missing`. Pins v25 / v26 / three shells. |
| Cond 4 | EPERM_OK | Confirm in `OUT` and in the seal. |
| Cond 7 | BLOCKED still seals | Line: a BLOCKED build still seals and is reported BLOCKED. |

SQL pin remains `b10d6cfd90b0586070c5a4ed3df5cd9782d2d7ad6e6145dcc3719f67a3d5e5c0`.
Bytes are the attached v3 file (not invented).
