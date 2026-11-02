# ccecea74 — P-1..P-5 + X-3 trace (v2.3)

Ruling: v2.2 PASS WITH CONDITIONS. Closed: X-1 / X-8 / X-9, X-2,
X-4..X-7. Mac execution allowed at **PLUMBING-ONLY** on a `b1d857d3`
worktree (W4–W6 RETRO + W8 PROSPECTIVE-RESEARCH). v2.3 is a **small
diff + files**. Builder, seal, and W7 were **not run**.

Weekly averaging: **code wins** — unweighted mean of weekly rates over
last N completed REG team-weeks. Play counts are sample size for the
backbone only. (v2.2 path text that said "play-weighted" was corrected.)

| Cond                                                                             | v2.2                                                 | v2.3                                                                                                                    |
| -------------------------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| P-3 stamp **both** helper shas; v21 = `05027146…`                                | Only v22 `HELPER.sha256`                             | `HELPER_V21.sha256` + `HELPER_V22.sha256` + `HELPERS.json` in the seal; mismatch → BLOCKED                              |
| X-3 local W vs prod W-1 + genuine export                                         | Authored W5/W6 sample; same-week join; no tolerances | Team-form join local W ↔ prod W-1; `PARITY_TOLERANCES`; no export → `NOT_RUN_NO_PROD_EXPORT`; authored samples refused |
| P-1 external sha; runner reads `OUT/store`                                       | External sha; digest of whatever path was passed     | `resolve_feature_store` prefers `OUT/store`; pin is the store digest copied **outside**                                 |
| P-2 W8 before 2026-10-29 20:15 ET; exclude kickoff ≤ seal                        | Deadline constant + exclude `kickoff <= capture_ts`  | Refuse to **start** W8 at/after `2026-10-30T00:15:00Z`; still exclude games at/before seal time                         |
| P-5 missing finals BLOCKED; re-run = new snapshot; BLOCKED build → no sealed run | Missing finals BLOCKED; timestamped OUT              | `refuse_blocked_build`; builder writes `BUILD_BLOCKED` and exits 6; `RERUN_IS_NEW_SNAPSHOT=true`                        |

Export spec for Platform Reliability / Ryan:
`scripts/nfl/imv/nfl-imv-prod-export-spec-v2.3.md` (query, columns, weeks
3–7, `kind=sealed_prod_feature_export`).

Mac commands: `scripts/nfl/imv/nfl-imv-mac-runbook-v2.3.md` (P-4 tar+sha
to `~/Desktop`).
