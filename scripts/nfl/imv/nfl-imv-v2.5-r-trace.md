# 54ba672b — v2.5 reader R-1..R-9 + C-3/C-4 close

IMV v2.4 filing sha `54ba672b`. Reader and runbook were RETURNED.
v24 `7c3f4dc7` is frozen. New helper: `nfl_imv_v25.py`.
Builder / seal / W7 / parity evidence were **not run**.

| ID | Ask | v2.5 |
| --- | --- | --- |
| R-1 | Main SELECT 41 cols, not 9-col CTE | Depth-aware outermost / COPY SELECT. Assert vs `PINNED_V3_COLUMNS`. |
| R-2 | Types fixed | Per-column int/date/bool/str/float. Bad cell → NOT_RUN. Bool t/f only. |
| R-3 | Roof-flagged rows block cert PASS | `n_roof_not_run > 0` → `NOT_RUN_ROOF_VOCAB`. |
| R-4 | Rest raw/derived | `schedule_game_date − *_prev_reg_game_date`. Mismatch → `REST_RAW_DERIVED_MISMATCH`. NULL prev unmatched. |
| R-5 | Exported dups + row count | `schedule_dup_game_rows>0` or per-key>1 → FAIL. `export_row_count` must equal parsed rows. |
| R-6 | STL/SD/OAK + unparseable game_id | `FAIL_TEAM_CODE`. LA/WSH/JAC still alias. |
| R-7 | No cert tolerance override | `tolerances=` on cert → `TOLERANCE_OVERRIDE_REFUSED`. |
| R-8 | REPORTED + plumbing status | `evidence_label=REPORTED`. Plumbing PASS → `PASS_PLUMBING`. |
| R-9 | Exact v3 sha, export sha, build-start | `query_sha` must be `b10d6cfd…` only. `meta.sha256` required. Missing build-start → NOT_RUN. |
| C-3 | Cert 0.005, no loosen | Closed via R-7. |
| C-4 | Capture / as-of / sha / after-build | Closed via R-9. |
| K-1..K-4 | Runbook | `nfl-imv-mac-runbook-v2.4.1.md`. No `rm -rf`. |

D-1 (bye / cross-season mix) and D-2 (withdrawn fixtures) are in the
deviation register.
