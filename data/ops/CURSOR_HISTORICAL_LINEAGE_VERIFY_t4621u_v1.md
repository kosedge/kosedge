# CURSOR_HISTORICAL_LINEAGE_VERIFY_t4621u_v1 — DRAFT (read-only)

**PAPER ONLY · CERT=0 · NFL NO-GO · F2 PHI@WSH FROZEN · Coming Soon ON · #648 DRAFT · do not merge**

Filed 2026-10-28. Cursor (cloud eng) seat. No Exp D-R touch. No Odds. No holdouts. No redesign. No register writes. No merge/deploy.

Alex SPEC **5ad4f170** executed exactly (§5 A–E). Codex contract addendum **085c92e9** bound (parent SPEC unmodified). CoS ACCEPT of both filed. IMV assessment **74c97d4c** ACCEPTED — REQUIRE_REPROBE returns below.

```text
❌ BAD: treat warehouse CURRENT ROW as sealed EPA/G34 SoT; auto-void grades; re-run Exp A/D-R; pull Odds
✅ GOOD: hash sibling + #646 emit; C1 kickoff-strict W-L; D/B file probes; FAIL_CLOSED when PBP/$R papers absent
```

---

## 0) Authority / tips / box

| item | sha8 / SHA | status |
|---|---|---|
| COS_ORDER_CURSOR_t4621u | **54acf54f** | MATCH `54acf54fe24a8170712dd0420da67cadb12fa00b1db5041439ced09fff1b4a50` |
| ALEX_HISTORICAL_LINEAGE_SPEC_t4621u_v1 | **5ad4f170** | MATCH `5ad4f170acbd31bc7cda98d096c4df8bf5414d40fa25b1754ff3f62857018d01` |
| CoS ACCEPT of SPEC | cited | filed (upload) |
| ALEX Codex contract addendum | **085c92e9** | MATCH `085c92e9d0ff6a4df6a15760843e976e01853215108940958c8cea3d06f3c7c5` |
| CoS ACCEPT of addendum | cited | filed |
| CoS Codex recon | **44d80837** | MATCH `44d80837157b99f0a64997bcd99cd11fabf764561c7aadf302e925d4cc82a34f` |
| Codex independent audit | **30734490** | MATCH `307344903fa9ed0b10036e8db8ae4db7e4ddfc65d905a8b56d76dc6b8be4caa1` |
| DECISION | **095d17df** | cited (source file not remounted) |
| IMV assessment | **74c97d4c** | cited by CoS bind; file not remounted on this VM |
| #648 DRAFT tip (this paper start) | **dc415cf6** | `dc415cf6fd9ae9a4ec8a607617fb1ff4b986e77f` (≥ required) |
| `origin/deploy-vercel` tip (resolved this filing) | **bfc89f57** | `bfc89f57b118ed2e480f3bde8a0c3a281a2341ad` (= Codex pin) |
| #646 emit tip | **a027cc7d** | `a027cc7d43008fa2c107dd2e27924ba7c178f247` (fetched `cursor/epa-wf-feature-emit-5bcd`; cite, not merge) |
| Exp E H1 tip | **0940a289** | `0940a28941959c77d510c05e9e56198a08812869` |

`$R=/workspace/ops/nfl_enterprise_green_t4359u/` is **absent** on this VM (same as prior #648 papers). Registers `/workspace/kosedge-registers/` absent. No directory invented under `ops/`.

**Resolution used (read-only):** sibling #648 paths under `research/nfl/` + `git show` of #646 emit (not a merge). PBP parquet cache `/tmp/nflverse-pbp-exp-e` **empty** — B1/B4/C2 numeric recomputes **FAIL_CLOSED**. No nflverse download.

Institutional memory: **no prior grades** for this verify product. Forward-only. Prior research grades (db42ad49, 5878136c, f1fa86e7, 0d1f4f9b, 3d79c41b, 04869644, 81a6727d) **PRESERVED**. This paper does not auto-void any grade (SPEC §6 / addendum §5).

---

## 1) IMV REQUIRE_REPROBE — headline returns

| # | probe | result | one-line |
|---|---|---|---|
| 1 | **C1** RECORD entering-record | **PASS** | 2992/2992 exact W-L vs kickoff_utc < row kickoff_utc, same season |
| 2 | **C2** G34 n0 shrink counts | **FAIL_CLOSED** | no PBP on box; source path is kickoff-honest (`hist = sk < ko_ts`) |
| 3 | **D1–D4** G34 select∩eval | **PASS** + **T4 flag** | folds prior-only; 2023 absent from `grid_mae`; cfg picked on same ≤2022 OOF that is binding MAE (Lane A vs Lane B) |
| 4 | **B1–B5** T1 row probes | **mixed** | B2/B3/B5 **PASS**; B1/B4 **FAIL_CLOSED** (no PBP) |
| 5 | **E1–E3** retro labeling | **PASS / MISSING** | rows lack `forecast_ts`; papers/manifests on box label RESEARCH / packet emit; sealed SPEC papers A1/A6 not on box |
| 6 | **A1–A9** hashes | **mixed** | sibling + #646 pins MATCH; `$R` Alex/IMV papers **FAIL_CLOSED** |

Exp D-R packet **untouched**. Warehouse F1 CURRENT ROW **still present** on both tips (identical blobs) — **Lane A / non-SoT**; does not by itself kill sealed grades.

---

## 2) Checklist table (binding output)

`check_id | threat | PASS/FAIL/FAIL_CLOSED | evidence path+sha8`

| check_id | threat | result | evidence path+sha8 |
|---|---|---|---|
| A1 | T5 | **FAIL_CLOSED** | `$R/ALEX_EPA_WALKFORWARD_EVAL_2013_2023_t4564u_v2.md` **88b3b7ce** not on this VM |
| A2 | T5 | **PASS** | #646 `git show` emit `epa_wf_features_2013_2023.csv` **02f6b2e2**; rolling **1b07654e**; `manifest.json` **3073dd96**; `MISSING.json` **e036c0fe**; `DATABASE_URL_BLOCKER.json` **5ba0b759**. Sibling rolling `research/nfl/t4586u_exp_e_inputs/rolling_features_weekly_pbp_strict_asof_2013_2023.csv` **1b07654e** (byte-identical). `$RD/SHA256SUMS` at a027cc7d lists the same pins |
| A3 | T5 | **PASS** | `research/nfl/t4586u_exp_e_inputs/historical_oos_games.csv` **1ee90fac**; rolling **1b07654e** |
| A4 | T5 | **FAIL_CLOSED** | outputs on `research/nfl/t4602u_exp_a/` MATCH: predictions **c3248302**, selected_cell **3172b236**, manifest **11b161c4**, fold_table **380538a5**, betas **8fbeaa7c**, counts **b60deb6a**, metrics_binding **1cac09ff**, metrics_2023 **76b94beb**, stop_rule **e14e235d**, grid_mae **170cec7a**. Inputs H2 **db2cf4b2**, games **4fe1cdd7**, oos **1ee90fac**, emit **02f6b2e2**, H1 sums **97774e08** MATCH. PBP 2012–2023 parquet **absent** — cannot `sha256sum -c SHA256SUMS.inputs` |
| A5 | T5 | **PASS** | `research/nfl/t4586u_exp_a_h2_manifest_freeze/CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json` **db2cf4b2** (also `research/ops/` + `data/ops/`) |
| A6 | T5 | **FAIL_CLOSED** | RECORD/R1/eval-record papers **5878136c / fb3fba40 / f1fa86e7** not on this VM |
| A7 | T5 | **FAIL_CLOSED** | IMV/RCA/DFG papers **0d1f4f9b / 3d79c41b / 04869644 / 81a6727d / a7f00a8d** not on this VM (grades cited, files not remounted) |
| A8 | T5 | **PASS** | `MISSING.json` **e036c0fe**: warehouse rolling 2013–2022 **BLOCKED** (no `DATABASE_URL`); offline PBP bypass labeled `not_warehouse_table`. `DATABASE_URL_BLOCKER.json` **5ba0b759**: same probe (local 5432 refused; Railway names-only). Maps to T5 provenance — warehouse path not used for sealed emit |
| A9 | T5 | **PASS** | `git cat-file -t a027cc7d` = commit; `0940a289` = commit. Emit script at a027: `scripts/nfl/emit_epa_wf_pbp_strict_asof_t4564u.py`. **0940a289 has no emit script** (E H1 addendum tip, expected) |
| B1 | T1/T5 | **FAIL_CLOSED** | cannot recompute `off_epa_per_play_5g` / `def_epa_allowed_per_play_5g` from PBP (cache empty, no download). Supporting only: all 5,984 rolling rows `asof_policy=strict_prior_weeks_unweighted_weekly_mean_last5` **1b07654e**; `games_in_window_5` = 5 for all rows; `n_gt_5=0` |
| B2 | T1 | **PASS** | `week1_windows.csv` **08ef1fa3** n=350 (175 games × 2). 2013 week-1 first/last years = **2012 only** (32/32). No week-1 row has same-season `first`/`last` token |
| B3 | T1 | **PASS** | emit **02f6b2e2** n=2992; rolling join (season, week, canon team) missing = **0**; policy is weeks < week (no week+1 join) |
| B4 | T1 | **FAIL_CLOSED** | G34 `rating_diff_home` recompute from PBP needs parquet; absent. Identity check only: `pm_A = β·rating_diff + HFA·home_ind` on **c3248302** 2725/2725 (max \|err\| 5.0e-7) |
| B5 | T1 | **PASS** | `intraweek_conservative.csv` **a67c89e2** n=14541; note 14541/14541 = `same (season,week) earlier kickoff excluded by week <`; self-exclude=0; `kickoff_unknown.csv` **d8cece63** n=0; all intra `game_id` ⊂ emit |
| B6 | T5 | **FAIL_CLOSED** | cannot refit β/HFA to 1e-6 without fold rating-walk + 2013 design rows (predictions start 2014). **n_design** vs prior-season counts from emit: F1–F9 **9/9 MATCH** (267…2423). Code: `design = seasons < S` in `t4602u_exp_a_execute.py` |
| C1 | T3 | **PASS** | recompute `record_entering_home/away` from `games.csv` **4fe1cdd7** + oos scores **1ee90fac** (2013–2023 only; 2992 score keys; miss_score=0). Rule: same season, kickoff_utc < row kickoff_utc, W-L (ties omitted in stored `W-L` strings). **2992/2992 exact**. emit vs games record mismatch=0. `pit_record_rule=walkforward_wl_after_game_same_season` on all emit rows |
| C2 | T3 | **FAIL_CLOSED** | n0 shrink observation counts not re-instrumented (no PBP). Source (`walk_rating_diffs`): `hist = sk < float(ko_ts)` then `fit_joint(..., n0=λ*4)`; G34 n0=8.0. Season-final posterior used only as **next-year** prior. Numeric sample as B4 not run |
| C3 | T3 | **PASS** | `games_in_window_5` vs min(5, prior team-games with (season,week)<target) from games **4fe1cdd7** + 2012 sidecar: **0** rows exceed cap (n=5984) |
| C4 | T3 | **PASS** | emit script at a027 groups `["season","week",posteam/defteam]` and windows `(season,week) < target` — not season-total. Warehouse `odds_lake.py` `groupby("season")` hits are **out of lineage** (justified, not FAIL) |
| D1 | T4 | **PASS** | H2 **db2cf4b2** outer folds F1–F9, S=2014…2022; `ratings_train` / `fit_beta` = seasons < S; 2023 supportive-only / cannot-alone-PASS; 2024+ forbidden. No separate inner-CV season table — “inner-CV MAE” **is** pooled ≤2022 OOF |
| D2 | T4 | **PASS** | `grid_mae.csv` **170cec7a** fields = cfg knobs + mae + n_oof (2440); **no 2023 column/aggregation**; 54 cells G01–G54. 2023 only in `metrics_2023.json` **76b94beb** (`label=2023_supportive`) |
| D3 | T4 | **FAIL** (oos file only) | emit **02f6b2e2**: train_le_2022 n=2707 ∩ check_2023 n=285 = ∅; union=2992. games/roll/pred season≥2024 = **0**. **oos 1ee90fac contains 586 rows season ∈ {2024,2025,2026}** — literal `awk '$1>=2024'` ≠ 0. Those rows were **not** used in C1/EPA/G34 panel (filtered). No separate 2024+ holdout file opened |
| D4 | T4 | **PASS** + flag | H2 freeze commit `d854ac52` (12:53Z) **before** Exp A packet `6f1fe16b` (13:10Z). `selected_cell.json` + metrics **same commit** (execute order: grid → winner → metrics_2023). Tie-break in selected_cell matches H2. **Flag:** G34 cfg chosen by min pooled ≤2022 OOF MAE (= binding reported MAE n=2440) → Lane A cell-pick on Lane B sample (addendum §4). β itself is prior-seasons-only. IMV decides qualification |
| E1 | T2/T5 | **PASS** (MISSING fields) | EPA emit: no `forecast_ts` / `generated_at` / `asof_ts` (kickoff_utc + pit_* only). G34 predictions: no kickoff/asof. G34 manifest `forecast_ts_utc=2026-10-28T13:09:29Z` (packet emit). EPA manifest `forecast_ts_utc=2026-10-27T21:36:59Z` (run emit). Inventoried as **MISSING**, not a grade FAIL (SPEC E1) |
| E2 | T2 | **FAIL_CLOSED** | papers **88b3b7ce / 5878136c / 0d1f4f9b** not on box. On-box labels: emit `research_label=RESEARCH_DIAGNOSTIC` 2992/2992; G34 `REPORT.md` “Paper/file evidence only”; H2 `execution=false` at freeze; no contemporaneous-issuance wording found on mounted artifacts |
| E3 | T5 | **PASS** | all 2992 emit rows `pit_schedule_sha256=1ee90fac…` = hashed oos **1ee90fac** on box. Path `data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv` — labeled historical/retro, not pre-season live capture. File also holds 2024–26 rows (see D3) |
| E4 | T2/T5 | **FAIL_CLOSED** | `f1fa86e7` not on box. Gap vs SPEC-stated minimum: see §4 |
| E5 | T6 | **PASS** | `market_line_source` distinct = {`historical_oos_ms9_nflverse_close`} on emit **02f6b2e2** and games **4fe1cdd7** (2992/2992). mm on G34 pred is joined market; no Odds pull |

---

## 3) Addendum §2 map (F1–F4 → T1–T4)

| Codex | threat | Cursor checks | this return | Lane | sealed-artifact impact |
|---|---|---|---|---|---|
| F1 CURRENT ROW (ingest + `historical_market_backtest` same-week join) | T1 | B1–B5 | Warehouse **CONFIRMED still present** on **dc415cf6** and **bfc89f57** (identical blobs). Sealed CSV probes: B2/B3/B5 **PASS**; B1/B4 **FAIL_CLOSED**. No same-week row found in sealed rolling/emit/intraweek | Warehouse = **Lane A DEVELOPMENT_ONLY / non-SoT**. Sealed EPA/G34 = offline strict-prior (recon SUPERSEDED_FOR_RESEARCH **pending B1 numeric**) | Grades **not** killed by F1 alone |
| F2 backdated `projection_created_at` | T2 | E1–E2 | On-box artifacts label retro/research; row `forecast_ts` **MISSING**. Sealed SPEC papers not remounted | Reconstruct ≠ live issuance (Lane B forbids treating reconstruct as live) | Preserved **if** missing papers hold the same label (E2 FAIL_CLOSED) |
| F3 present-day completed-game counts | T3 | C1–C4 | **C1 PASS** (decisive RECORD). C3/C4 PASS. **C2 FAIL_CLOSED** (G34 n0 not numerically sampled) | Prod `_load_team_strength_priors` out of sealed path | RECORD T3 **PASS** on this box. G34 shrink counts still **PENDING** numeric |
| F4 backtest weight ∩ eval | T4 | D1–D4 | Warehouse script still selects/reports on same join (Lane A, non-fireable). G34: fold β prior-only **PASS**; cfg selected on reported ≤2022 OOF — **T4 flag** (Lane A cell-pick / Lane B score overlap) | G34 binding MAE is the selection metric | IMV decides whether cfg∩OOF disqualifies Lane B claim. 2023 not in grid |

F5–F10 out of scope (addendum).

### F1 CURRENT ROW — tip cite (no code change)

| surface | #648 DRAFT `dc415cf6` | `deploy-vercel` `bfc89f57` |
|---|---|---|
| `services/model-service/data_platform_nfl/ingest.py` blob | `31e0da1e0d1d155d04d5d76a6e73df3e8756e4d5` | **same blob** |
| `CURRENT ROW` windows | L1308–1403 (2/4 PRECEDING AND CURRENT ROW) | **same lines** |
| `scripts/nfl/historical_market_backtest.py` blob | `550d168397d1665ef3c6bffe6547a08c6271da9a` | **same blob** |
| same-week join | L223 `hf.week = sch.week` | **same line** |

Sealed rolling CSV: `source=nflverse_pbp_pass_run_offline`, `not_warehouse_table=True`, `asof_policy=strict_prior_weeks_unweighted_weekly_mean_last5` (5984/5984). Warehouse remat **quarantined** until CLEAR (recon). **No repair in this paper.**

---

## 4) E4 gap table (vs SPEC-stated minimum; f1fa86e7 unread)

| field | SPEC / E1 read | emit 02f6b2e2 | G34 pred c3248302 | G34 manifest 11b161c4 |
|---|---|---|---|---|
| `forecast_ts` / `generated_at` / `asof_ts` | required by f1fa86e7 (unverified here) | **MISSING** | **MISSING** | `forecast_ts_utc` = packet emit 2026-10-28T13:09:29Z |
| `kickoff_utc` | present | present | **MISSING** (join games **4fe1cdd7**) | n/a |
| `pit_schedule_sha256` / `pit_record_rule` | present | present (1ee90fac / walkforward_wl_after_game_same_season) | n/a | n/a |
| `season` / `week` / `game_id` | present | present | present | n/a |
| fold / cfg | n/a | n/a | present (G34 only in this file) | `selected_cfg_id=G34` |

---

## 5) Lane A vs Lane B (addendum §4)

| artifact | lane | why |
|---|---|---|
| Warehouse `historical_market_backtest.py` blend-on-eval + CURRENT ROW join | **DEVELOPMENT_ONLY** | F1+F4 CONFIRMED; non-fireable until repair + IMV |
| H2 54-cell grid **db2cf4b2** | frozen design (Lane A allowed) | frozen at `d854ac52` before scoring |
| G34 cfg pick (min inner-CV MAE = binding OOF) | **DEVELOPMENT_ONLY** for the *cell choice* | selection sample = scored n=2440 |
| G34 fold β / HFA (seasons < S; n_design MATCH) | construction OK for Lane B *if* IMV accepts pre-reg grid + post-hoc cell | 2023 supportive-only; 2024+ unused in pred/emit |
| EPA train_le_2022 vs check_2023 | disjoint (**PASS D3a**) | union 2992 |
| EPA/G34/E sealed CSVs vs warehouse | research SoT ≠ warehouse | F1 SUPERSEDED_FOR_RESEARCH pending B1 numeric |

Research PASS ≠ CERT. Historical `cert_eligibility=NONE` (a7f00a8d unread here; cited).

---

## 6) Interpretation (SPEC §6 — binding)

1. **No confirmed sealed-CSV contamination** on C1 / B2 / B3 / B5 / C3. Warehouse F1 remains a confirmed **code-path** defect, not a sealed-CSV FAIL.
2. Missing PBP / `$R` papers → **FAIL_CLOSED** for those checks only. Does **not** imply PASS or FAIL of prior grades.
3. D3 oos 2024–26 rows and D4 cfg∩OOF are **flags for IMV**, not auto-voids.
4. Nothing here lifts CERT. NFL NO-GO. F2 frozen. Coming Soon ON.
5. Exp D-R STOP **6bd07cc8** / counts **1b9dc93c** — **untouched**.

---

## 7) Codex fold-in (SPEC §7 — filled this filing)

| finding_id | Codex claim | applies_to | confirmed_vs_hypothesis | owner | impact | verification_ref |
|---|---|---|---|---|---|---|
| F1 | CURRENT ROW + same-week backtest join | warehouse; not sealed emit | **CONFIRMED** on dc415cf6 **and** bfc89f57 (identical blobs). Sealed T1 row probes PASS where runnable | Cursor quarantine (no CLEAR) | warehouse non-SoT; sealed grades stand pending B1 | B2/B3/B5; §3 |
| F2 | backdated reconstruct | prod; research labeling | **CONFIRMED** prod (unread tasks.py this paper). Research labels retro on mounted artifacts | Alex/IMV | E2 papers unread | E1–E2 |
| F3 | present-day counts | prod CONFIRMED; research was HYPOTHESIS | RECORD **C1 PASS**. G34 n0 **still FAIL_CLOSED** | IMV | RECORD T3 closed on this box | C1–C4 |
| F4 | select ∩ eval | warehouse CONFIRMED; G34 was HYPOTHESIS | G34 cfg picked on binding OOF — **flag**. β prior-only PASS | IMV | Lane A vs B for cell, not for β | D1–D4 |

---

## 8) Non-goals / confirmations

- No Exp D-R packet edit, re-run, or STOP change.
- No Odds. No 2024+ holdout file opened (oos season column counted only).
- No G34 promotion. No CERT lift. No register writes. No code change.
- Parent SPEC **5ad4f170** not edited.
- Probe script lived under `/tmp/t4621u_readonly/` only; results JSON committed beside this paper.

**CERT=0. RESEARCH_DIAGNOSTIC. NFL NO-GO. F2 frozen. Coming Soon ON.**
