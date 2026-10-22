# NFL model-validation complete trace (t4175u / t4179u / t4183u)

**Filed:** 2026-10-22  
**Aligned to:** IMV plan sha `53e7aba3`  
**Frozen predictive criteria:** `4f832c91` + `132ee26c` under protocol `6a3aa3d9`  
**Not criteria:** `c57032db` (G2 feature-parity only)  
**This filing:** trace + prep. **No** evaluation, grading, certification run, download, or production access.

Verdict vocabulary (t4179u): **CLEAN** | **CONTAMINATED** | **UNKNOWN**.  
CLEAN requires a sealed row list, as-of proofs, and train-only isolation. None of those exist for a 2,998-game result.

Performer numbers stay **REPORTED**. NFL remains **NO-GO**.

---

## Executive findings

1. **There is no 2,998-game result in this public repo.** GitHub code/issues/PRs, `origin/deploy-vercel`, and Notion workspace search do not contain `V1_CERTIFICATION_PASS` or n=2998. IMV: *n=2998 is UNSUPPORTED* (`53e7aba3` LC-2).
2. **The attested neighbor is n=2992 train / 570 test / 3562 corpus (2013–2025).** That 2992 equals the **2013–2023** row count in `historical_oos_games.csv` (filed 2026-09-16). Row-level identity of “CSV 2013–2023” vs “July 28 supervised train” is **UNKNOWN** (no game_id list on the July 28 artifact).
3. **That 2992/3562 work is CONTAMINATED** as certification evidence: same-week rolling join (L-1), uncapped week when pack week is null (L-2), closing lines used as sim features, blend weights swept on the **full** 3562 including the later “test” years, 2024–25 holdout ruled contaminated by IMV (`78f5ee7e`).
4. **No historical season has verifiable point-in-time inputs** for the production fair path (no per-feature `as_of < kickoff_utc` proof table).
5. **No season is untouched** once it entered the 2013–2025 warehouse used for fit/sweep/gates, except **pre-2013** (not in those scripts) and **2026 W8+** (IMV G4; capture **not built**). 2026 W1–W3 were used in production remat / OOS diagnostic. 2026 W4–W6 are plumbing-only and out of this track.

---

## 1. t4179u — 2,998-game result, step by step

### 1.1 Identity of the claimed result

| Item | Verdict | Evidence |
| ---- | ------- | -------- |
| A file of 2,998 game_ids + sha + created-at | **UNKNOWN** | Not in repo, not on `origin/deploy-vercel`, not in GitHub search, not in Notion search (2026-10-22). IMV R-6 / `f4c61237` cited only by sha; those files are **not in this public repo**. |
| Status string `V1_CERTIFICATION_PASS` | **UNKNOWN** | Zero matches in tree. |
| n=2992 supervised train | **CONTAMINATED** (in-sample) | `data/ops/nfl-kav-supervised-retrain-v3.json` `train_rows: 2992`, `generated_at` 2026-07-28T14:28:10Z; commit `0694840115e287e301b8912ef0048c37e05cb38c` (2026-07-28). IMV: *Train 2992 is IN-SAMPLE*. |
| n=3562 completed-with-lines corpus | **CONTAMINATED** (used for weight sweep) | `data/ops/nfl-market-blend-backtest-2026-07-17.json` `sample_size: 3562`; commit `1f9d454ce408ac568ef321f077b8de26b9cf00b2` (2026-07-17). |
| n=3578 OOS diagnostic rows | **CONTAMINATED** (research; includes 2024–26) | `data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv` (3578 data rows); commit `2a0d875f909d9dff7c3a085f91b2f424282cef61` (2026-09-16). Verdict in packet: `MODEL_SIGNAL_WEAK`, not a CLEAR. |

**What 2998 is not:** 2992, 3562, 3578, 1693, 1931, 586, 570, 285.

### 1.2 Which games and seasons it used

| Claim | Verdict | Evidence |
| ----- | ------- | -------- |
| 2998 seasons/weeks/game_ids | **UNKNOWN** | No list. |
| 2992 = 2013–2023 completed slate in the Sept 16 OOS CSV | **CLEAN as a count**; **UNKNOWN as row-level identity with the July 28 train set** | Season counts in `historical_oos_games.csv`: 2013–2019 = 267×7 = 1869; 2020 = 269; 2021 = 285; 2022 = 284; 2023 = 285; **sum = 2992**. 2022=284 matches the cancelled Bills–Bengals game. July 28 JSON has `train_start_season: 2013`, `rows_seen: 3562`, `train_rows: 2992`, `test_rows: 570` and **no game_ids**. 2024+2025 in that CSV = 285+285 = 570. Arithmetic is consistent; **join of the two artifacts was not run** (no eval). |
| Inclusion filter for 3562 | **CONTAMINATED** (post-game required) | `scripts/nfl/historical_market_backtest.py` SQL: `home_score IS NOT NULL AND away_score IS NOT NULL AND spread_line IS NOT NULL AND total_line IS NOT NULL`, seasons 2013–2025. Same completed-score filter in `tasks._fetch_nfl_supervised_training_rows`. |

### 1.3 Used in development, tuning, or feature selection before “evaluation”

| Step | Verdict | Evidence |
| ---- | ------- | -------- |
| 2998 used as an unused test | **UNKNOWN** | No 2998 list to compare. |
| 2992 used as **train** | **CONTAMINATED** | `fit_nfl_supervised_models` (`nfl_supervised_retrain.py`) fits win/total/margin GBMs on `train_rows`. Feature keys (41, schema v3) selected on that matrix. |
| Full 3562 used to **choose blend weight 0.30** | **CONTAMINATED** | `historical_market_backtest.py` sweeps weights on all rows; artifact 2026-07-17 recommends 0.30; `nfl_simulator.py` lines 25–28 cite that sweep. **2024 and 2025 are inside that sweep.** |
| 2024 used as blend **tune** after being in the 3562 sweep | **CONTAMINATED** | `scripts/nfl/tune_blend_weights.py` docstring: tune 2024 (~285), test 2025 (~285). `nfl-vegas-benchmark-report.json` (2026-07-17) same split. 2024 was already in the same-day full-corpus sweep. |
| 2025 labeled “touched once” | **CONTAMINATED** | Same: 2025 is in the 3562 sweep (`sample_size: 3562`, `end_season: 2025`) **and** the vegas-benchmark “test”. IMV: 2024/2025 holdout is CONTAMINATED (`78f5ee7e` C-1). |
| HFA 1.05 / prior total 45.3 | **CONTAMINATED** | Comments in `nfl_handicapping_framework.py` 76–82: tuned after 2023–2025 ATS / totals audit. |
| PLAY band `spread_play_v2_cap7` | **CONTAMINATED** (selection) | Confirmatory 2024–25 PLAY n=227 in `nfl-play-only-holdout.md` (2026-07-28). IMV: no cert weight. |

### 1.4 Point-in-time (`as_of < kickoff`)

| Input | Verdict | Evidence |
| ----- | ------- | -------- |
| 2998 per-row proofs | **UNKNOWN** | No proofs. |
| Rolling EPA / matchup pack | **CONTAMINATED** | L-1: `ingest.py` window `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` + join `h.week = s.week`. Backtest joins the same way. Live remat caps priors at **game week** (`tasks.py` `as_of_week=matchup_pack.week`). |
| Uncapped rolling lookup | **CONTAMINATED** when week is null | L-2: `_week_cap_nullable_predicate` allows `week_cap IS NULL` → latest week of the season. |
| KAV | **CLEAN as a join rule**; **UNKNOWN as applied to 2998/2992 rows** | `kav.py` / `docs/NFL_KAV.md`: week−1 only. Holdout report claims KAV week−1. No per-row `kav_as_of_week` table on the July 28 artifact. |
| Rest in the 3562 backtest | **CONTAMINATED** | `historical_market_backtest.py` sets `rest_days_home=7.0`, `rest_days_away=7.0` for every game. |
| Rest/injury in supervised rows | **CONTAMINATED** (L-3) | `_fetch_nfl_supervised_training_rows` defaults rest 7.0 / injury 0.0. |
| Warehouse odds (if used as features) | **CLEAN rule, UNKNOWN coverage on 2992** | `.cursor/rules/nfl-historical-warehouse.mdc`: strictly before kickoff. The 3562 default path uses **nflverse `spread_line`/`total_line`**, not the owned lake. |

### 1.5 Closing lines or post-game data as features

| Use | Verdict | Evidence |
| --- | ------- | -------- |
| nflverse close as **sim feature** | **CONTAMINATED** | `full_pipeline_holdout_backtest.py` 11–13, 214; `tune_blend_weights.py` 178–181; production `simulate_nfl_game(..., market_spread_home=..., market_total=...)`. |
| nflverse close as **label / MAE comparator** | **CLEAN as a grade**; **UNKNOWN capture time** | Legitimate for M-1(b) *comparison* if not also a feature. IMV: nflverse capture time not per line → V-2 **NOT AVAILABLE** for market-comparison **cert**. |
| Final scores as features | **CONTAMINATED** if same-week rolling includes the game (L-1); **CLEAN** as labels | Scores are required for the 3562 inclusion filter (selection on completed games — survivorship of “has a final”). |
| Season-level 2026 packaged EPA inside 2026 | **CONTAMINATED** if used as in-season as-of | Pack `as_of=2026-08-08` in OOS diagnostic; not a weekly PIT. |

### 1.6 Selection bias in which games were included

| Filter | Verdict | Evidence |
| ------ | ------- | -------- |
| Require final score + closing spread + closing total | **CONTAMINATED** | Drops cancelled / no-line games (2022 n=284 not 285). Conditions on a close existing. |
| PLAY-only n=227 | **CONTAMINATED** | Band selected after seeing 2024–25 confirmatory ATS/CLV. |
| Supervised usable rows | **CONTAMINATED** | Drops rows without `home_team_won` / `final_total_points` (`fit_nfl_supervised_models`). |
| 2998 inclusion rule | **UNKNOWN** | No list. |

### 1.7 What 2992/3562 **legitimately** demonstrates (and does not)

**Reproducible?** **Partial, not bit-for-bit.** Scripts exist; they need a populated warehouse (`nfl_dp_schedules`, rolling/matchup tables, optional fit row). No sealed input manifest (R-2). No game_id sha for the July 28 train set.

**Demonstrates (REPORTED only):**

- A 2013–2025 completed-with-nflverse-lines corpus of **3562** games was used to sweep a market-blend weight; **0.30** minimized MAE vs **actual scores** on that **same** corpus.
- A chronological 16% cut of that corpus yields **2992 / 570** for the schema-v3 GBM. Holdout Brier/MAE cleared the **secondary** floors in `docs/NFL_ENTERPRISE_GATES.md` (2026-07-28). Those floors **cannot** replace market-relative gates (`53e7aba3` §1).
- 2013–2023 in the Sept 16 OOS CSV **counts** to 2992. That is a count, not a cert.

**Does not demonstrate:**

- A leakage-free, unused, 2,998-game certification.
- That the model beats close **without** using the close as a feature.
- G4 prospective skill. Enterprise overall gate on 2026-07-28 is **RED** (`nfl-enterprise-gates-latest.md`).

---

## 2. Season / range classification (t4179u)

Three **exclusive** buckets. “Verifiable PIT” means a sealed `as_of < kickoff` proof for the production feature set. **No season qualifies.**

| Range | Bucket | Why |
| ----- | ------ | --- |
| pre-2013 | **Untouched** by the 3562/2992 scripts | `START_SEASON = 2013`. Whether older nflverse exists in a private warehouse: **UNKNOWN**. |
| 2013–2023 | **Used for dev/tuning** | Supervised train (2992 count); full blend sweep; HFA/total prior comments cite 2023–25; OOS trailing chapter for 2023 (n=285). |
| 2024 | **Used for dev/tuning** | In 3562 sweep; blend **tune** year; confirmatory PLAY; IMV contaminated holdout. |
| 2025 | **Used for dev/tuning** | In 3562 sweep; labeled test; PLAY primary; 370-game KAV re-sim; IMV contaminated. |
| 2026 W1–W3 | **Used for dev/tuning** | Production remat + OOS diagnostic n=16 W1 (`historical_oos_by_season.csv`). |
| 2026 W4–W6 | **Neither** (plumbing-only) | IMV C-5. Not a predictive set. This track does not read those bundles. |
| 2026 W7 | **UNKNOWN** | Not classified in IMV S-3 (W8+). Whether remat already touched it: **UNKNOWN** without production access. |
| 2026 W8+ | **Untouched as G4** | Capture **not built** (P-10). Untouched ≠ graded. |
| 2027+ | **Untouched** | Future. |

Walk-forward **diagnostic** (G3) after LC-1..LC-3, if Ryan approves P-1: IMV allows 2013–2023 folds only, still **never cert**. Genuinely unused evaluation: **2026 W8+ sealed** (and later), not 2024–25.

---

## 3. (A) Complete prediction process

Production game fairs: **not** `nfl_season_engine`. Path = remat → `simulate_nfl_game` → `nfl_market_projections` → `GET /nfl/fair-lines`.

### 3.1 Raw → team ratings

| Stage | Path / function | Formula / parameters |
| ----- | --------------- | -------------------- |
| Ingest PBP / schedules | `data_platform_nfl` CLI; `ingest.py` | nflverse / nflreadpy → `nfl_dp_play_by_play`, `nfl_dp_schedules` |
| Situational weekly | usage materializer | team-week EPA, success, pressure, pass rate from PBP |
| Rolling 3g/5g | `materialize_matchup_features_from_usage` | `AVG(...) OVER (PARTITION BY team ORDER BY season, week ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)` — **includes current week** |
| Offense/defense index | `tasks._load_team_strength_priors` / backtest `_offense_defense_index` | `offense = clamp(1 + 0.75*off_epa + 0.18*pressure_delta, 0.82, 1.22)`; `defense = clamp(1 + 0.90*(-def_epa_allowed) + 0.14*pressure_delta, 0.82, 1.24)` |
| True-PR blend | `_load_team_strength_priors` | Prior-season rolling + current-season rolling (week-capped) + continuity / QB premium; optional replace with packaged 2026 EPA JSON |
| KAV | `data_platform_nfl/kav.py` | Iterative opponent-adj EPA through week W; **features join W−1**. `KAV% = (adj_epa − league_mean) / 0.15` |
| Injury nowcast | `nfl_injury_nowcast.fetch_nfl_injury_nowcast` | Multipliers; **divide** into defense index (not multiply). Missing → 0.0 impact |
| Early-season overlays | `overlays_must_stay_off` | KAV / second-order / nowcast stripped before 3 completed REG games (`tasks.py` 4693–4713) |

### 3.2 Ratings → expected scoring

`compute_nfl_projection_decomposition` (`nfl_handicapping_framework.py`, version `nfl-handicap-core-v3.1`):

```
off_def_home = clamp(off_home / max(0.75, def_away) - 1, -0.25, 0.25)
off_def_away = clamp(off_away / max(0.75, def_home) - 1, -0.25, 0.25)

base_margin = clamp((off_def_home - off_def_away)*16.0 + 0.35*spread_signal, -6.5, 6.5)
base_total  = clamp((off_def_home + off_def_away)*10.5 + 0.28*total_signal + totals_components, -5.0, 5.0)

predicted_margin = Σ factor.margin_points
predicted_total  = clamp(45.3 + Σ factor.total_points, 30, 66)
expected_home    = max(7.5, (predicted_total + predicted_margin)/2)
expected_away    = max(7.0, (predicted_total - predicted_margin)/2)
```

Default factor parameters (env-overridable):

| Factor | Default | Status (2026-08-25 freeze) |
| ------ | ------- | -------------------------- |
| HFA | +1.05 margin | ON |
| Rest | 0.18 pts/day margin, cap 2.0; missing filled 7.0 | ON |
| Injury | weights 2.75 / 3.25; caps 2.6 / 2.8 | ON when overlays on |
| Weather | wind −0.07 total / mph; precip −0.12; cap 2.8 | ON, fallback-safe |
| Travel | 0.0016 margin / mile; 0.28 / TZ | ON |
| KAV | 3.2 / 2.4; caps 3.5 / 2.8 | ON (locked) |
| Travel×weather | bounded | ON (locked) |
| Personnel / coach / info velocity | weights exist | **OFF** (killed) |
| External DVOA | 0.0 | OFF |

### 3.3 Expected scoring → fairs, probabilities, edges

`simulate_nfl_game` (`nfl_simulator.py`):

```
for i in 1..N (default 4000; backtest 1200/1500):
    home ~ max(0, N(expected_home, σ))
    away ~ max(0, N(expected_away, σ))
σ = clamp(9.8 + totals_stdev + error_regime_widen, 7.6, 12.2)

# Market blend if a line is present (FEATURE):
w_s = clamp(0.30 + early_week_boost + side_disagreement_boost, 0, 0.85)
  early_week_boost: W1 0.25, W2 0.20, W3 0.15, W4 0.10
margin_post = (1-w_s)*margin_pre + w_s*(-market_spread_home)
total_post  = (1-w_t)*total_pre  + w_t*market_total

spread_home     = -mean(margins)
total_mean      = mean(totals) then slate totals calibration
home_win_prob   = mean(margin > 0)
fair_ml         = American from that probability
```

Then optional `apply_supervised_blend` (GBM, weeks 5+, real features) and `apply_totals_calibration` (slate level shift).

`annotate_projection_model_handicap`: `model_*` = pre-blend when diagnostics exist; `handicap_*` / DB columns = published KEI.

**Edge (locked in lab protocol):** `edge_pts = kei_spread_home − market_spread_home`. Publish tags: `nfl_side_total_publish_policy.py` — default PASS; spread PLAY only if `2.5 ≤ |edge| < 7.0` and gates allow; totals PLAY off.

Fair-lines read path: `routes/nfl.py` `_nfl_fair_lines_impl` → web `fetchNflFairLines` → Edge Board. Week-1 KEI read-time reprice is **identity** on published columns.

Season engine (`project_game_player_boxes`, `simulate_full_season`) is **player / survivor / true-PR desk**, not this board.

---

## 4. (B) Dataset inventory

Coverage numbers below are **from in-repo artifacts**, not a live warehouse query. Warehouse row counts on Railway today: **UNKNOWN**.

| Dataset | Where | Coverage (attested) | Quality / timestamps | PIT | Missingness / limits | Used in tuning? |
| ------- | ----- | ------------------- | -------------------- | --- | -------------------- | --------------- |
| **PBP** | `nfl_dp_play_by_play`; ingest `013_nfl_pbp_normalized.sql` | Scripts materialize 2013+; QB attempt flags “~2022–25” (`nfl-qb-continuity-holdout-probe.json`) | nflverse vintage **UNKNOWN** (no R-2 pin) | Game is post-facto; weekly as-of is week grain | No `offense_personnel` (factor freeze B). Tendency cols need `034` backfill | **Yes** — EPA, KAV, tendencies |
| **Schedules** | `nfl_dp_schedules`; OOS CSV | OOS CSV 2013–2025 = 3562; +2026 W1 = 16. Per season: §1.2 | Finals + nflverse `spread_line`/`total_line` | Kickoff present on product path; hist close **time UNKNOWN** | 2022 one cancelled game; scores required for 3562 | **Yes** |
| **Odds snapshots** | `odds_snapshots`; lake under gitignored `data/nfl/warehouse/`; HD path in `nfl_warehouse/paths.py` | Owned OC **1931** games (2020–25 mix) after densify (`nfl-owned-oc-densify-2020-2023.json`, 2026-07-28). 2013–19 owned OC **thin / UNKNOWN** | `available_at` required for warehouse features | Rule CLEAN (before kickoff) | Key rotation **DEFERRED**; 2026-09-04 live audit: `oddsPersisted` events/snapshots/history = **0** on www | **Yes** for CLV/PLAY; **not** the 3562 default close (nflverse) |
| **Players / usage** | `nfl_dp_player_game_stats`, `nfl_dp_player_usage_weekly` | Player-week backtests e.g. 11,453 records (matchup-engine folder) — **not** game-line n | Identity graph `021` | Weekly | Preseason hydrate synthetic (`preseason_hydrate_v1`) | **Yes** for props/spine; **indirect** for game fairs (QB premium / depth) |
| **Injuries** | `nfl_dp_injuries`; nowcast | Hist coverage **UNKNOWN** | Freshness hours on nowcast | Not sealed per game | Default 0.0 (L-3); neutralized early season | **Yes** as a feature; often off |
| **Rosters / depth** | `nfl_dp_rosters`; packaged `nfl_depth_chart_2026_w1.json`; `historical/` depth packs 2019–2025 | Depth packs exist for replay | NFL.com preferred; nflverse fallback | Week-1 / weekly inferred | Camp churn; WR4+ caps | Season engine / props; **not** Edge Board sim |
| **Transactions** | `nfl_txn_sot_scan.py` (PFR/Sleeper) | Desk as-of dates | `as_of_date` on events | Daily grain | Not a 3562 feature | Desk / SoT; **UNKNOWN** if in 2992 matrix |
| **Weather / travel** | Open-Meteo via `nfl_environment.py`; `nfl_game_context` | Live path best-effort | Forecast as-of ≠ sealed hist archive | **No hist weather archive in repo** | Missing → factor unavailable | Weights exist; hist backtest **does not pass weather** |
| **Market movement** | Open vs close; `n_snaps≥2` | CLV n=601 spread after densify (2026-07-28 gates) | Movement-only definition locked | Open/close snaps | 2013–19 movement **UNKNOWN**; 2020–22 CLV+ failed (0.45) | **Yes** — PLAY policy |
| **Existing model outputs** | `nfl_market_projections`; `data/ops/nfl-season-engine-launch-*`; fair-lines stamps | 3562 outcomes cited; 20,740 projections in one KAV sprint note (local DB, 2026-07-28) | `created_at` sometimes wall-clock after the game (walkforward leakage counter exists) | Stamp check ≠ feature PIT | July-31 freeze multi-season **UNREPRODUCIBLE** (OOS diagnostic) | **Yes** — cal, gates, PLAY |

Packaged 2026 EPA/backbone JSON: season-level, used when `prefer_packaged_epa=True`. **Used** in 2026 remat and Sept 16 OOS.

---

## 5. (C) Deficiencies (ranked by expected OOS accuracy impact)

Propose no new factor unless it beats a missing-data or leakage fix. Rank is **expected impact**, not a measured lift (no eval this pass).

| Rank | Deficiency | Type | Why it moves OOS | Evidence | Propose? |
| ---- | ---------- | ---- | ---------------- | -------- | -------- |
| 1 | L-1 same-week rolling join | Leakage | Week-W EPA includes game W — in-sample ratings, optimistic MAE | `ingest.py` window + `week = week` join; backtest SQL | **Fix join** (already specified). No new factor. |
| 2 | Close used as a **feature** then graded vs close | Leakage / contamination | Blend 0.30 + W1–4 boost shrinks toward the label | `simulate_nfl_game` 602–645; sweep on 3562 | **Report two numbers**: raw vs blended. Do not add features. |
| 3 | 2024–25 used for tune **and** test | Contamination / overfitting | Weight 0.30 and PLAY band saw those years | 2026-07-17 artifacts; IMV 78f5ee7e | **Exclude from cert.** G3 only on 2013–23 after L-1/L-2. |
| 4 | No timestamped hist close (V-2) | Missing data | Cannot certify market-relative MAE/CLV | IMV M-1; nflverse no per-line time; Odds keys deferred | **Acquire** owned snaps (plan §6). |
| 5 | No as-of proof table | Leakage control missing | Cannot prove PIT | No file on July 28 artifacts | **Emit proofs** (validator exists; not run on hist). |
| 6 | Hist injury/rest/weather missing or defaulted | Missing data | Rest=7 and injury=0 hide real week-to-week variance; weather unused in 3562 backtest | L-3; backtest hardcodes rest 7 | **Flag** (done). Fill only from dated feeds. |
| 7 | Personnel killed — no `offense_personnel` in public PBP | Feature gap | Cannot adjust for 11/12/13 personnel | Factor freeze 2026-08-25 | **Do not re-enable** until a PIT personnel source exists. |
| 8 | Opponent adjustment only via KAV; rolling EPA is raw | Adjustment | SOS bias in early weeks / weak KAV coverage | KAV week-1 null; QB flags 1075/3562 | Prefer **using lagged KAV correctly** over new ratings. |
| 9 | Early-season overlays off + extra market blend | Contamination + missing | W1–4 fairs are mostly market | `overlays_must_stay_off`; blend boost | Honesty, not a new model. |
| 10 | PLAY-band selection | Selection / survivorship | 227 games ≠ slate | `nfl-play-only-holdout.md` | Do not widen. |
| 11 | Pre-2023 packaged-prior gap | Missing data | OOS: packaged priors cannot be built ≤2023 | `HISTORICAL_OOS_DIAGNOSTIC.md` | Accept as DATA_INSUFFICIENT; don’t invent. |
| 12 | July-31 freeze unreproducible across seasons | Reproducibility | Cannot rebuild that stamp hist | OOS diagnostic | Ignore for cert. |

**2998 reproducibility:** **Not reproducible** (no list, no generator sha). **2992/3562:** scripts + DB, **not** sealed. **Demonstrates:** in-sample / contaminated hist MAE and a secondary holdout GREEN — **not** an unused cert.

**Periods:**

| Use | Periods |
| --- | ------- |
| Development (already spent) | 2013–2025, 2026 W1–W3 |
| Walk-forward **diagnostic** after L-1/L-2 + P-1 | 2013–2023 folds only (G3, never cert) |
| Genuinely untouched evaluation | 2026 W8+ sealed (P-10) and later; **n≥200 not reachable in 2026 REG** (IMV §10) |

---

## 6. (D) Missing-data acquisition plan

No downloads in this pass. Costs are **public list prices / in-repo estimates**, not quotes.

| Priority | Data | Source | Cost (public) | PIT capability | Why |
| -------- | ---- | ------ | ------------- | -------------- | --- |
| P0 | Per-feature as-of proofs on a **rebuild** (2013–23 diagnostic) | Derived from owned warehouse after L-1/L-2 | $0 (compute) | Yes if `as_of < kickoff` enforced | Unblocks LC-1 |
| P0 | Ryan rulings P-1/P-2/P-5/P-6 | — | $0 | n/a | Gate |
| P1 | Timestamped hist closes (spread/total/h2h) | The Odds API historical, **after key rotation** | ~10 credits / region / market / request; in-repo NFL 2000–25 estimate **84,000** credits if that history exists — docs say history often starts **~2020** (`docs/HISTORICAL_ODDS_CREDITS_ESTIMATE.md`) | Yes if `available_at` stored | V-2 market comparison |
| P1 | Pin nflverse release (schedules, PBP, lines) | nflverse / nflreadpy | Free (GitHub) | Week/game grain; **close time still weak** | R-2 manifest |
| P2 | Hist injury + inactives with publish time | nflverse injuries + NFL.com inactives | Free / NFL.com auth | Only if snapshot time kept | L-3 |
| P2 | Hist weather archive | Open-Meteo archive (free) or stadium logs | Free tier typical | Reanalysis ≠ forecast; store **forecast issued-at** if used as a feature | Weather factor is live-only today |
| P3 | Personnel (11/12/13) | Not in public nflverse PBP (freeze B). Licensed PBP **UNKNOWN** cost | UNKNOWN | Must be pre-kickoff | Do **not** buy unless P0–P1 done |
| P3 | SportsData / other paid SoT | Not on the game-line path today | UNKNOWN | UNKNOWN | Do not add a second SoT |
| — | c57032db Railway export | Internal | $0 | Feature parity, **not** predictive | P-9; owner Railway/PR |

**Do not** pull Odds history until P-3 (key rotation) and Ryan P-2. **Do not** put closes in the feature tree (LC-6).

---

## 7. Prep bytes (unchanged track rules)

- Rebuild contracts + as-of validators + expanding-window splits + runner v2: `services/model-service/src/services/nfl_eval_prep/`
- L-1/L-2 diff: `docs/research/NFL_EVAL_PREP_L1_L2_LEAK_FIX_DIFF.md`
- Tests: synthetic only (`tests/test_nfl_eval_prep.py`)
- Production ingest/remat **not** rewritten
- `scripts/nfl/imv/` not created
- W4–W6 plumbing not read

---

## 8. Gap list (critical path)

| # | Gap | Impact | Effort | Owner |
| - | --- | ------ | ------ | ----- |
| G0 | Ryan P-1/P-2/P-5/P-6 | Blocks every gated run | Decision | Ryan |
| G1 | 2998 list still missing | Claim stays UNSUPPORTED | Small if off-repo; else re-earn | Cursor / Alex |
| G2 | Apply L-1/L-2 materializer on sealed 2013–23 **local** lake | Stops same-week ratings | Medium; needs R-2 pin | Cursor after P-1 |
| G3 | R-2 nflverse + lake pins | Reproducibility | Medium; no download until authorized | PR / Ryan |
| G4 | P-9 Railway / c57032db | G2 parity only | UNKNOWN | Railway / PR |
| G5 | P-3 + hist closes | Cert market MAE/CLV | Ops | Ryan / PR |
| G6 | P-10 W8+ seal | Only clean G4 | Medium | PR / Cursor |
| G7 | Full 803ceb4e memo vs these bytes | UNKNOWN clauses | Small once readable off-repo | Cursor |
| G8 | Blind IMV metric script | LC-4/5 | Medium | CoS / IMV |
| G9 | 0444 pre-reg | Freeze before G3 | Text | IMV / Ryan |

---

**UNKNOWN (explicit):** off-repo 2998 file; IMV memo full text; Railway ETA; live warehouse counts; 2026 W7 remat touch; SportsData on this path; licensed personnel cost; row-level equality of July 28 train vs Sept 16 2013–23 CSV.
