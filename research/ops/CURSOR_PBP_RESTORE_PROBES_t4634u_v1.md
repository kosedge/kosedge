# CURSOR_PBP_RESTORE_PROBES_t4634u_v1

**PAPER ONLY · CERT=0 · NFL NO-GO · F2 PHI@WSH FROZEN · Coming Soon ON · #648 DRAFT · do not merge**

Filed 2026-10-28. Cursor (cloud eng) seat. Completes lineage FAIL_CLOSED checks **C2 / B1 / B4 / A4** after restoring sealed nflverse PBP. No new predictive experiment. No nested G34. No Odds. No F2. No SoT change. No merge/deploy.

```text
❌ BAD: treat warehouse CURRENT ROW as SoT; download nflverse HEAD after pin mismatch; touch Mac cert PBP
✅ GOOD: pin-gated restore of 2012–2023 only; sha256sum -c; recompute B1/B4/C2 vs sealed CSVs; stop
```

---

## 0) Authority / tips / box

| item | sha8 / SHA | status |
|---|---|---|
| DECISION_RYAN_t4634u | **1cf303e3** | cited (order authority) |
| COS_ORDER_CURSOR_t4634u | **2693c91b** | MATCH `2693c91b0452196a076e4cb16be8a1459928b81db0da037c70223db3057f77b4` |
| Feasibility packet | cited | uploads `COS_FEASIBILITY_AUTH_PACKET_t4634u_POST_LINEAGE_v1.md` |
| Lineage verify procedure | **ebd3ea93** | MATCH sibling `CURSOR_HISTORICAL_LINEAGE_VERIFY_t4621u_v1.md` |
| H1 sums file pin | **97774e08** | MATCH `research/nfl/t4586u_exp_e_kickoff_asof/SHA256SUMS` |
| SHA256SUMS.inputs (Exp A) | **7e2a494b** | MATCH upload `SHA256SUMS.inputs` and `research/nfl/t4602u_exp_a/SHA256SUMS.inputs` |
| #648 DRAFT tip (this paper start) | **f24e3614** | `f24e3614` lineage-verify commit; this filing appends |

`$R=/workspace/ops/nfl_enterprise_green_t4359u/` **absent**. Optional E2/E4 **FAIL_CLOSED** (papers not remounted). Registers `/workspace/kosedge-registers/` absent. Mac cert PBP `823304ba…` **not touched**. Warehouse CURRENT ROW **not used as SoT**.

Institutional memory: **no prior grades** for this restore-probe product. Forward-only. Prior grades (including lineage ebd3ea93, Exp E 3d79c41b, Exp A packet) **PRESERVED**. This paper does not auto-void any grade.

---

## 1) Restore path

**Used: pin-matched re-fetch.** Preferred prior Exp E cloud cache `/tmp/nflverse-pbp-exp-e` was **empty** on this VM (same absence that left t4621u C2/B1/B4/A4 FAIL_CLOSED).

Fallback authorized by t4634u: re-fetch from the same nflverse release URL family Exp E used,

`https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet`

for seasons **2012–2023 only**. Each file was hashed before any parquet parse. **12/12 sha256 exact-match** sealed pins. No vintage drift. No “latest if close.” No purchase. Parquets staged read-only under `/tmp/nflverse-pbp-exp-e` (gitignore; ~229 MB; **not committed**).

| season | bytes | sha8 | pin |
|---|---|---|---|
| 2012 | 19322039 | **447b9078** | MATCH |
| 2013 | 19521610 | **f454605a** | MATCH |
| 2014 | 19360792 | **54c01408** | MATCH |
| 2015 | 19545842 | **01b5ae7d** | MATCH |
| 2016 | 19344382 | **95eba04e** | MATCH |
| 2017 | 19050401 | **84eacd96** | MATCH |
| 2018 | 19072097 | **2e6f2dce** | MATCH |
| 2019 | 19119729 | **60c30670** | MATCH |
| 2020 | 19286459 | **8889f5d8** | MATCH |
| 2021 | 20249925 | **333ad343** | MATCH |
| 2022 | 20426548 | **931121d8** | MATCH |
| 2023 | 20534088 | **bd348473** | MATCH |

Receipt: `research/nfl/t4634u_pbp_restore_probes/SHA256SUMS.restored_pbp`.

---

## 2) Headline returns (this filing)

| # | probe | prior ebd3ea93 | this filing | one-line |
|---|---|---|---|---|
| 1 | **A4** input hash verify | FAIL_CLOSED | **PASS** | `sha256sum -c` 12/12 PBP + H1 sums **97774e08** + sibling inputs MATCH |
| 2 | **B1** EPA 5g recompute | FAIL_CLOSED | **PASS** | reconstructed rolling vs **1b07654e**: n_vintage=0; same-week in window=0; n_gt_5=0; 2024+ plays=0 |
| 3 | **B4** G34 `rating_diff_home` | FAIL_CLOSED | **PASS** | 2725/2725 vs **c3248302**; max \|Δrd\| 5.0e-11; pm_A identity 2725/2725 (max 5.0e-7) |
| 4 | **C2** G34 n0 shrink counts | FAIL_CLOSED | **PASS** | `hist = sk < ko_ts`; n_future=0; n_same_game=0; n0=8.0=λ·4; season-final = next-year prior only |
| — | **E2 / E4** (optional) | FAIL_CLOSED | **FAIL_CLOSED** | `$R` papers still absent; not expanded |

No check flipped to substantive **FAIL**. IMV re-note not required by t4634u stop rule.

---

## 3) Checklist (binding output)

`check_id | threat | PASS/FAIL/FAIL_CLOSED | evidence path+sha8`

| check_id | threat | result | evidence path+sha8 |
|---|---|---|---|
| A4 | T5 | **PASS** | `SHA256SUMS.inputs` **7e2a494b**; H1 sums **97774e08**; PBP 2012–2023 12/12 MATCH (table §1). Sibling MATCH: games **4fe1cdd7**, oos **1ee90fac**, emit git-show **02f6b2e2**, rolling **1b07654e**, H2 **db2cf4b2**, predictions **c3248302** |
| B1 | T1/T5 | **PASS** | Exp E reconstruct (`strict_prior_weeks_unweighted_weekly_mean_last5`) vs sealed rolling **1b07654e**. weekly=6518; reconstructed=5984; n_vintage_mismatch=0; n_same_week_in_window=0; n_gt_5=0; n_plays_season_ge_2024=0 |
| B4 | T1 | **PASS** | G34 walk ρ=0.95 λ=2 n0=8 ρ_s=0.67. team_games=6518 (expect). panel=2992. rd MATCH 2725/2725 vs **c3248302** max \|err\| 4.9987e-11. `pm_A = β·rd + HFA·home_ind` 2725/2725 max \|err\| 4.999e-7 |
| C2 | T3 | **PASS** | Instrumented `walk_rating_diffs`: hist=`sk < ko_ts`; n_kickoffs=1336; n_hist min/median/max = 0 / 288 / 568; n_hist_zero=11 (week-1 prior-only); n_future_in_hist=0; n_same_game_in_hist=0; season_final_used_as_same_season_rating=0 |

JSON: `research/nfl/t4634u_pbp_restore_probes/CURSOR_PBP_RESTORE_PROBES_t4634u_v1.json`.

---

## 4) What this does **not** change

- Sealed Exp E **3d79c41b** / Exp A packet / Exp D-R **93a79857** FAIL_RESEARCH CLOSED — untouched.
- G34 Lane A DEVELOPMENT_ONLY (cfg∩OOF) from lineage D4 — **unchanged**. This filing only proves ratings/shrink counts are kickoff-honest on restored pins.
- Warehouse F1 CURRENT ROW still present on code tips — still **non-SoT**.
- NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · #648 stays DRAFT.
- W8 integration is a separate prior auth — not blocked, not expanded here.

---

## 5) Non-goals / confirmations

- No nested G34 run. No redesign. No Odds. No 2024+ holdout file opened (oos 2024–26 rows counted then dropped, same as Exp A).
- No Mac cert PBP. No paid data. No register writes. No deploy/publish.
- Probe script: `research/nfl/t4634u_pbp_restore_probes.py`. Does not rewrite `t4602u_exp_a/` or `t4586u_exp_e_kickoff_asof/` sealed outputs.

**CERT=0. RESEARCH_DIAGNOSTIC. NFL NO-GO. F2 frozen. Coming Soon ON.**
