# 47616a70 — C-1..C-6 trace (v2.4)

Ruling: deliver v2.4. Frozen helpers **v22=57a419b4**, **v23=fe66b374**.
Bundle every imported helper + feature-path + README. Runbook
**returned**. Builder / seal / W7 were **not run**.

| Cond | Ask                                                                | v2.4                                                                                                |
| ---- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| C-1  | zero matched rows → FAIL                                           | `FAIL_ZERO_MATCHED_ROWS` when `compared_team_weeks < 1` (`nfl_imv_v24.py`)                          |
| C-2  | only 10 of 14 comparable; rest/roof/EPA-diff separate              | Team join stays 10 keys. Separate: rest raw+derived + roof exact; `diff_off_epa == home-away`       |
| C-3  | tighter cert tols, separate from plumbing                          | plumbing 0.02/0.03; cert **0.005**. Cert PASS also needs ≥90% coverage + 100% separate (`c57032db`) |
| C-4  | export capture time, data as-of, SQL sha; reject after build start | `captured_utc` + `data_as_of` + `query_sha`; `FAIL_EXPORT_CAPTURED_AFTER_BUILD`                     |
| C-5  | pin v22=57a419b4 and v23=fe66b374; BLOCK mismatch                  | Full pins in `V22_PIN` / `V23_PIN`; builder + runner + `stamp_helper_shas`                          |
| C-6  | write store SHA256SUMS last                                        | `write_store_sha256sums_last` after helper stamps in `OUT/store`                                    |

Returned runbook (`nfl-imv-mac-runbook-v2.4.md`):

1. IMV folder outside BASE (never `$BASE/scripts`).
2. W8: re-pre-stage after W7 finals (after Mon 10-26), then build+seal before 2026-10-29 20:15 ET.
3. Box path `/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/` via `~/Desktop` CopyToBox; W8 tar before kickoff; retro tar before results discussion.
4. Store sha on box **before** each sealed run.
5. Tar only explicit stamp dirs; no parquet; include parquet sha manifest.
