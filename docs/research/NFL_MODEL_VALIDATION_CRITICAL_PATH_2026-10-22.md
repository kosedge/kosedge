# NFL model-validation critical path — preparation report

**Filed:** 2026-10-22  
**Authority:** Ryan user messages t4175u / t4179u / t4183u (2026-10-22) · Enterprise Model Standard  
**IMV plan aligned to:** sha prefix `53e7aba3` (`IMV_PLAN_NFL_PREDICTIVE_PERFORMANCE_REVIEW_t4175u`)  
**Complete trace (verdicts, process, datasets, acquisition):** [`NFL_MODEL_VALIDATION_TRACE_COMPLETE_2026-10-22.md`](./NFL_MODEL_VALIDATION_TRACE_COMPLETE_2026-10-22.md)  
**This document:** preparation index + R-6 list. **No** historical evaluation, grading, or certification run.  
**Repo posture:** public. No certification data, protected datasets, credentials, or server addresses.  
**NFL product posture (unchanged):** NO-GO. Coming Soon stays on until IMV independently clears the required gates.

Frozen predictive criteria are **`4f832c91` + `132ee26c` under protocol `6a3aa3d9`**.  
**`c57032db` is not the criteria.** It is the production-input feature-parity protocol (14 fields, 0.005-type tolerances, coverage ≥ 90%) and is a G2 input to this track only.

Evidence grade of this filing: **NONE (plan / prep)**. Performer numbers stay **REPORTED** (LC-5).

---

## 0. What this pass delivered

| IMV ask | Status |
| -------- | ------ |
| P-7 leakage-free rebuild **code** (LC-1..LC-3, L-1/L-2 fixed, L-3 flagged) at a pinned sha | **IN PREP → bytes in this PR.** Not run on evaluation seasons. |
| 803ceb4e local feature path + runner v2 bytes | **Delivered as prep bytes** under `nfl_eval_prep` / `scripts/nfl/eval_prep/`. |
| R-6 2,998-game trace list | **Answered item-by-item in §2.** n=2998 is **UNSUPPORTED**. |
| W4–W6 plumbing | **Not read, not written, not cited as predictive evidence.** |
| `scripts/nfl/imv/` | **Not present. Not created. Not modified.** |
| Historical / gated eval | **Not executed.** |

Pinned sha = the merge-base commit of this branch once pushed (`cursor/nfl-model-validation-prep-b241`).

---

## 1. Computation trace (production fairs / spreads / totals)

Published NFL sides, totals, and win% are **not** produced by `nfl_season_engine` season simulation. They come from a separate game-level Monte Carlo.

### 1.1 Ordered write path

| Step | Module | Function | What it does |
| ---- | ------ | -------- | ------------ |
| 0 | `src/tasks.py` | `pull_nfl_context_snapshot` | ESPN schedule → `games` + `nfl_game_context` (rest, weather/travel JSON, record-based indices) |
| 1 | `data_platform_nfl/ingest.py` | nflverse ingest + `materialize_matchup_features_from_usage` | `nfl_dp_schedules`, rolling EPA, matchup packs |
| 2 | `data_platform_nfl/kav.py` | `materialize_kav` | Opponent-adjusted EPA; **week−1 lag** on the pack |
| 3 | `src/tasks.py` | `run_nfl_market_simulations` | Per `game_date`: priors, pack, injuries, weather, sim, persist |
| 4 | `src/tasks.py` | `_load_team_strength_priors` | True-PR blend of rolling backbone + continuity/QB premium; optional packaged EPA JSON |
| 5 | `nfl_matchup_features.py` | `fetch_latest_matchup_feature_pack` / `matchup_pack_to_sim_input_kwargs` | Latest `nfl_dp_matchup_features_weekly` row → `NflGameInputs` |
| 6 | `nfl_injury_nowcast.py` | `fetch_nfl_injury_nowcast` | Team injury multipliers (often neutralized early season) |
| 7 | `nfl_environment.py` | `build_nfl_environment_context` | Open-Meteo weather + travel if context is empty |
| 8 | `nfl_simulator.py` | `simulate_nfl_game` | Decomposition → Gaussian MC → **market blend** → optional in-sim totals cal |
| 9 | `nfl_handicapping_framework.py` | `compute_nfl_projection_decomposition` | Factor sum → expected team points |
| 10 | `nfl_supervised_retrain.py` | `apply_supervised_blend` | Optional GBM overlay (gated: weeks 5+, real features) |
| 11 | `nfl_totals_calibration.py` | `apply_totals_calibration` | Slate-aware level shift on `total_mean` |
| 12 | `nfl_model_handicap.py` | `annotate_projection_model_handicap` | `model_*` (pre-blend) vs `handicap_*` (published) |
| 13 | Postgres | `nfl_market_projections` | Denormalized columns + `projection` JSONB |

Core math (`simulate_nfl_game`):

- `predicted_margin = sum(factor.margin_points)`
- `predicted_total = prior_total + sum(factor.total_points)`
- Scores ~ Gaussian around those means (`simulations` default 4000)
- `spread_home = −mean(home − away)`
- `home_win_prob` = fraction of sims with home score > away
- Fair ML from that probability
- If a market spread/total is present, shrink toward it (base weight 0.30; extra weight in weeks 1–4)

### 1.2 Ordered publish/read path

| Step | Module | Function |
| ---- | ------ | -------- |
| 1 | `routes/nfl.py` | `_nfl_fair_lines_impl` |
| 2 | SQL | `nfl_dp_schedules` ⋈ `games` ⋈ lateral latest `nfl_market_projections` |
| 3 | The Odds API | `fetch_odds` for compare-only market columns (`oddsMode=reuse` on the customer assemble path) |
| 4 | `nfl_model_handicap.py` | `resolve_model_and_handicap` |
| 5 | `nfl_kei_week1_reprice.py` | `apply_week1_kei_reprice_for_published_fair` — **identity / fail-closed** on published columns |
| 6 | `nfl_side_total_publish_policy.py` | PLAY/LEAN/PASS tags (spread band locked; totals PLAY off) |
| 7 | `apps/web/lib/nfl-fair-lines.ts` | `fetchNflFairLines` |
| 8 | `apps/web/lib/nfl-edge-board-from-fair-lines.ts` | Edge Board rows |

**KEI** on this sport is the published handicap (`handicap_*` / `spread_home` / `total_mean`), not a separate pack emitter.

**Season engine** (`simulate_full_season`, `project_game_player_boxes`) shares priors / packaged EPA. It does **not** replace `simulate_nfl_game` for Edge Board fairs (`nfl_season_engine/__init__.py`).

### 1.3 Input inventory

| Input | Where it comes from | Consumer | As-of / leakage note |
| ----- | ------------------- | -------- | -------------------- |
| Schedule + kickoff | `nfl_dp_schedules`; packaged 2026 schedule JSON; ESPN `nfl_data.fetch_nfl_schedule` | Context pull; fair-lines SQL | Time window on `games.start_time` |
| Record O/D indices | ESPN record → `team_strength_from_record` | `nfl_game_context` baseline | Weak; priors dominate |
| Rest days | Schedule lag; context columns | Decomposition `rest_travel` | **L-3:** missing → **7.0** |
| Weather / travel | `nfl_game_context.environment` or Open-Meteo | Framework weather/travel | Forecast as-of is not sealed per feature today |
| Rolling EPA / success / pressure | `nfl_dp_team_rolling_features_weekly` from situational weekly (nflverse PBP) | Priors + matchup pack | **L-1:** window includes `CURRENT ROW`; join is same week. **L-2:** `week_cap IS NULL` takes latest week of the season |
| Packaged EPA / backbone | `nfl_season_engine/data/nfl_team_epa_priors_2026.json`, `nfl_team_efficiency_backbone_2026.json` | Remat when `prefer_packaged_epa` | Season-level pack; not a per-game as-of |
| Matchup pack | `nfl_dp_matchup_features_weekly` | Simulator kwargs | Same-week rolling join (L-1) |
| KAV 5g | `nfl_dp_team_kav_weekly` via `kav.py` | Framework `kav_efficiency` | **Lagged week−1** (compliant). Stripped when overlays off |
| Second-order (personnel / coach) | Matchup pack | Framework (mostly off) | Documented week−1; overlays often off |
| Injuries | `nfl_dp_injuries` → nowcast | Framework + totals | **L-3:** missing impact → **0.0**. Neutralized before ≥3 REG games |
| PROE / tendencies | `fetch_team_proe_map` | Totals/spread tilt | Prior-season fallback; off when overlays off |
| Market spread/total **as a sim feature** | `nfl_market_history_snapshots` / live Odds API fallback | `simulate_nfl_game` blend | **Closing / live line is a feature**, not just a label. Early-week extra weight |
| Market **for publish compare** | The Odds API | Fair-lines board | Capture stamp exists on the web as-of path; not a sealed pre-kickoff ledger for hist eval |
| Open lines | First owned snap | Fair-lines open columns | Warehouse rule: strictly before kickoff |
| Totals calibrator | Historical `nfl_market_projections` + outcomes | `apply_totals_calibration` | Lookback env; uses outcomes — **must not fit on eval seasons** |
| Supervised fit | `nfl_supervised_model_fits` | `apply_supervised_blend` | Chronological last-16% of 2013–2025 (see §2). **2024–25 is the holdout and is CONTAMINATED** |
| Framework tuning tables | `nfl_framework_tuning_*` | Optional overrides | Off when overlays off |
| Active model version | `nfl_model_runtime_state` | Remat stamp | Default `nfl-v1.5-matchup-sim` |
| Depth / player spine | Season-engine packs | Props / fantasy **only** | Out of scope for game fairs |

SportsData as a game-line SoT: **not found** on this path (UNKNOWN if used elsewhere).

### 1.4 Calibration / overlay stack (what ships vs research)

| Layer | Shipped? | Note |
| ----- | -------- | ---- |
| True-PR prior blend | Yes | Shared with season engine |
| Matchup / totals point adjustments | Yes | Bounded |
| Market blend (0.30 + W1–W4 boost) | Yes | Uses market as a **feature**. Weight was swept on the 2013–2025 corpus |
| Supervised GBM overlay | Conditional | Off W1–4 / overlays-off |
| Final slate totals calibration | Yes | Production task defers the in-sim linear cal, then applies slate cal |
| `model_*` vs `handicap_*` | Yes | Research fair vs published KEI |
| Week-1 KEI read-time reprice | No-op on published columns | Fail-closed |
| PLAY tags | Policy only | `spread_play_v2_cap7`; totals PLAY off. Not a cert |

---

## 2. Prior-claim / R-6 2,998-game trace (item by item)

IMV (R-6): *If not traceable, n=2998 is RE-EARNED under this protocol and carries NO weight until then (78f5ee7e C-2; f4c61237).*

**Searched in this public repo (working tree + `origin/deploy-vercel` + GitHub code/issues/PRs):**  
`V1_CERTIFICATION_PASS`, `CERTIFICATION_PASS`, `2998`, `2,998`, `n=2998`, `scripts/nfl/imv/`, IMV sha files (`4f832c91`, `132ee26c`, `6a3aa3d9`, `c57032db`, `f4c61237`, `78f5ee7e`).

**Result:** none of those strings exist as a certification artifact or row list. IMV protocol text files are **not in this public repo** (cited by sha prefix only).

### (i) The row-list file (game_ids) with sha and creation timestamp

**MISSING.** No file of 2,998 game_ids, no sha, no creation timestamp.

Closest in-repo row counts (not a 2998 list):

| n | What | Path | Reproducible from repo alone? |
| - | ---- | ---- | ----------------------------- |
| **2992** | Supervised **train** rows (last-16% holdout complement) | `data/ops/nfl-kav-supervised-retrain-v3.json` (`generated_at` 2026-07-28T14:28:10Z) | Partial — needs warehouse DB + active fit path |
| **570** | Supervised **test** rows (2024–2025) | same JSON | Partial; **CONTAMINATED** (IMV 78f5ee7e) |
| **3562** | 2013–2025 completed games with nflverse closes | `data/ops/nfl-market-blend-backtest-2026-07-17.json`; `historical_market_backtest.py` | Partial — `DATABASE_URL` + `nfl_dp_*` |
| **1693** | Graded board games 2020–2025 | enterprise gates / spread lab | Partial |
| **1931** | Owned open/close games | gates JSON | Partial |

2992 + 570 = 3562. **2998 is not 2992, not 3562, and not 1693.**

### (ii) Generating code at a pinned sha

**MISSING for n=2998.**

Generating code **for 2992/570** exists:

- `services/model-service/src/services/nfl_supervised_retrain.py` → `fit_nfl_supervised_models` (`holdout_fraction=0.16`, sort by season/week/game_id, `train = usable[:-holdout]`)
- Row SQL: `tasks._fetch_nfl_supervised_training_rows` (2013–2025, `nfl_dp_matchup_features_weekly` ⋈ schedules)
- Blend corpus: `scripts/nfl/historical_market_backtest.py` (2013–2025, same-week rolling join)

That code is on `deploy-vercel`. It does **not** emit a 2998-row list. A pinned sha for a 2998 generator is **UNKNOWN** (not in this repo).

### (iii) Seasons and weeks covered

**UNKNOWN for n=2998** (no list).

For the nearest artifacts:

- Supervised matrix: seasons **2013–2025**, all weeks present in `nfl_dp_schedules` with final scores. Holdout is the last 16% by (season, week, game_id) → lands on **2024–2025** (570 games). Train 2992 is the prefix, **including 2024 weeks that sort before the cut** — exact week cut is **not pinned in a row list**.
- Blend backtest: 2013–2025, `home_score`/`away_score`/`spread_line`/`total_line` not null.

### (iv) Per-row as-of proof for features

**MISSING for n=2998.**

**MISSING for 2992/3562 as well.** Those scripts do not write `as_of < kickoff_utc` proofs. Rolling EPA is joined at the game week (L-1). KAV is week−1 (compliant when present). Rest/injury are defaulted (L-3). Market close is used as a **sim input** in the full-pipeline holdout.

This prep adds the LC-1 validator (`nfl_eval_prep.asof`) and runner-v2 exclusion of failing rows. It has **not** been applied to any historical corpus.

### (v) Pre-results split definition, if any

**MISSING for n=2998.**

For 2992/570: the split is **not** a pre-registered season fold. It is `holdout_fraction=0.16` after a chronological sort, coded in `fit_nfl_supervised_models`. IMV S-1 requires expanding-window **by season**, filed before results. That is **not** what produced 2992/570.

A separate 2024-tune / 2025-test blend-weight story lives in `data/ops/nfl-vegas-benchmark-report.json` (285-game 2025 slice). That retune-on-2024 is a **selection** pattern and is **CONTAMINATED** as holdout evidence.

This prep files S-1 expanding-window folds for **2013–2023 diagnostic seasons only** (`build_expanding_window_folds`). 2024–2025 cannot be eval folds. **Not run.**

### (vi) Overlap with the 2024/2025 holdout and with train 2992

**UNKNOWN for n=2998** (no game_id list to intersect).

If an off-repo “2998” were a near-miss for **2992**, then:

- Overlap with train 2992 = **identity** (in-sample; IMV: “Train 2992 is IN-SAMPLE”).
- Overlap with 2024/2025 holdout = **none by construction of the 16% cut**, except any 2024 games that fell **before** the cut and therefore sat in the 2992 train set. The number of such 2024 train games is **UNKNOWN** without regenerating the list (forbidden here: that would touch the contaminated holdout).

n=2998 is **UNSUPPORTED**. It carries **no certification weight**. Re-earn only under `6a3aa3d9` after P-1 and sealed inputs.

### 2.1 Other prior claims (do not treat as cert)

| Claim | In repo? | Reproducible? | Leak / bias flags |
| ----- | -------- | ------------- | ----------------- |
| `V1_CERTIFICATION_PASS` | **No** | n/a | n/a |
| Blend MAE edge, 3562 games, 2026-07-17 | Yes (JSON + script) | Partial (DB) | Same-week join (L-1); weight sweep on full corpus; closes as blend target |
| Supervised holdout GREEN (Brier 0.148, n=570) | Yes | Partial | **CONTAMINATED** 2024–25; closes in full-pipeline; same-week features |
| PLAY ATS 73.1% n=227 / later 63.9% citations | Yes / IMV notes later figures | Partial | Selection on PLAY band; IMV: **no cert weight** |
| Enterprise gates overall **RED** (2026-07-28) | Yes | Gate math yes | Full-slate ATS RED; MAE GREEN is market-relative on a contaminated board |
| Fair Lines production-cert 2026-09-17 **NO CLEAR** | Yes | Smoke only | Unbound `run_id`; not a hist eval |
| Phase 3 historical replay 2019–2025 | Yes | Partial | Season-level player scorecards; Vegas win totals missing |
| Walk-forward in `run_nfl_walkforward_backtest` | Yes | Partial | Checks `created_at < completed_at` only — **stamp** leakage, not feature L-1/L-2 |

Closing lines as **features**: production sim + `full_pipeline_holdout_backtest.py`. Legitimate as a *market-blend product* description; illegal if sold as an unassisted model fair.

Season-level packs (2026 EPA JSON) used inside a season: **risk** if treated as in-season as-of.

Retune on test: blend sweep on 2013–2025; 2024 used as a tune year in the Vegas-benchmark writeup.

Selection: PLAY-only confirmatory slice.

### 2.2 Required retraction list

IMV 78f5ee7e §4 is **not in this public repo**. CoS owns N-5 (assemble citation sites). This pass does **not** edit marketing copy or gates JSON. Places in-repo that a later retraction pass must visit (N-5 assist, not a claim they already say “2998”):

- `data/ops/nfl-kav-supervised-retrain-v3.json` (`train_rows: 2992`)
- `data/ops/nfl-kav-holdout-report.md`
- `data/ops/nfl-vegas-benchmark-report.json`
- `data/ops/nfl-enterprise-gates-latest.{json,md}`
- `docs/NFL_ENTERPRISE_GATES.md` (2024–25 PLAY holdout language)
- `nfl_simulator.py` header comment (“3,562 real games”)
- `docs/ops/NFL_FAIR_LINES_PRODUCTION_CERT_PRODUCT_2026-09-17.md` (unrelated product cert; do not conflate)

---

## 3. Prerequisites (leakage-free chronological hist eval)

Statuses: **present** / **missing** / **needs decision**. Owners from IMV §7.

| # | Prerequisite | Status | Owner | Notes |
| - | ------------ | ------ | ----- | ----- |
| P-1 | Written approval of plan scope + S-1..S-3 splits | **Needs decision** | Ryan | OPEN. This prep files the S-1 design; it does not approve it. |
| P-2 | Close-source ruling + M-2..M-5 conventions | **Needs decision** | Ryan | Candidates: (a) timestamped Odds snapshots (fails V-2 without capture time + keys); (b) nflverse `spread_line`/`total_line` (no per-line capture time → market comparison **NOT AVAILABLE** under V-2); (c) other licensed feed. IMV recommends (a) after key rotation. |
| P-3 | Odds API key rotation + authorized hist snapshots | **Missing** | Ryan / PR | DEFERRED-ROTATION. No fetch in this pass. |
| P-4 | Named results source (nflverse finals) for grading | **Needs decision** | Ryan | OPEN for new seasons. Grading files must stay physically separate (LC-6). |
| P-5 | Adopt or reject PR-1..PR-4 + new calibration metrics **before results** | **Needs decision** | Ryan | Totals/ML **not certifiable** until adopted. |
| P-6 | Bootstrap gating unit (by week vs game) | **Needs decision** | Ryan | IMV proposes cluster-by-week; 4f832c91 allows either if pre-registered. Seed 4141 / 10k resamples is in the frozen text, not in this repo. |
| P-7 | Leakage-free rebuild code, L-1/L-2 fixed, L-3 flagged, pinned sha | **Present (bytes)** | Cursor | This PR. **Not run** on 2024/2025 or any real slate. |
| P-8 | Local feature path + tree check (803ceb4e) | **Present (bytes)** | Cursor | `nfl_eval_prep.local_path` + `local_tree_check`. Status `LOCAL_TREE_CHECKED` is **not a gate** (C-8). Full 803ceb4e text is **not in this public repo**. |
| P-9 | Prod-parity export (`c57032db`) | **Missing / BLOCKED** | Railway / PR / Ryan | Feature-parity, **not** predictive criteria. In-repo: no c57032db packet, no 14-field export path under that name. Blocker named by IMV as Railway. Required action (from plan): Railway recovery, then Ryan-authorized v3 export. Expected completion: **UNKNOWN** (no Railway access in this pass). |
| P-10 | Automated prospective pregame capture (G4 / 2026 W8+) | **Present (bytes / dry-run)** | Cursor / PR / custodian | `nfl_w8_capture`. Live seal still needs operator snaps + custodian receipt. |
| P-11 | 2,998 trace bundle | **Missing** (answered as unsupported) | Cursor / Alex | §2. No bundle to seal. |
| P-12 | Blind-reimplementation roles | **Needs decision** | CoS / Ryan | LC-4. Not this PR. |
| P-13 | Pre-registration filed 0444 | **Needs decision** | IMV drafts / Ryan | IMV N-1. |
| P-14 | IMV metric script spec + synthetic self-test | **Needs decision** | IMV | N-2. This repo’s synthetic tests cover **prep validators**, not IMV’s metric script. |
| Data versions | nflverse / owned lake pin (URL, tag, retrieval UTC, sha) | **Missing** | Cursor / PR | R-2. Do not download in this pass. |
| As-of snapshotting | Per-feature source timestamp + sealed proof table | **Missing** on hist path; **present** as validator | Cursor | LC-1. Production remat does not emit the table. |
| Split design | Expanding-window by season, train-only | **Present as code**; **needs Ryan lock** | Cursor / Ryan | S-1. 2013–2023 diagnostic only. |
| Calibration outputs | ECE/Brier/logloss/AUC + MAE vs close | **Needs decision** on thresholds; emitters exist in other scripts | Ryan / IMV | Secondary floors in `docs/NFL_ENTERPRISE_GATES.md` cannot replace market-relative gates. |
| Closing-line source for comparison | See P-2 | **Needs decision** | Ryan | Must not enter the feature builder (LC-6). |

### 3.1 Frozen gates (in force; not re-opened here)

From IMV (132ee26c / 4f832c91), applied under `6a3aa3d9`:

- **SPREAD GREEN:** n ≥ 200 **and** model spread MAE ≤ market close MAE (market-relative; no absolute escape hatch). Whole CI must clear. Below min-n → **INSUFFICIENT-N**, never PASS.
- **SPREAD RED:** > 15% worse than close MAE, **or** \|bias\| > 3.0.
- **CLV GREEN:** n_clv ≥ 200 (`movement_only_n_snaps_ge_2`; soft segment floor 40).
- 95% CI. Break-even 0.5238. Stretch 0.55.
- Secondary (cannot replace market-relative): holdout margin MAE ≤ 9.5, total MAE ≤ 10.5, Brier ≤ 0.22; ATS n ≥ 200; CLV+ ≥ 0.55 at n ≥ 200; PLAY ATS n ≥ 60.

2024–25 holdout figures carry **no certification weight**.

G4 honesty (IMV §10): 2026 W8–W18 + playoffs cannot reach spread n ≥ 200. Earliest n ≥ 200 is **not claimed here** (UNKNOWN pending capture). Historical G3 is **diagnostic only** and cannot substitute for G4.

---

## 4. Prep work (no gate)

Implemented in this PR. **Synthetic data only.**

| Piece | Path |
| ----- | ---- |
| As-of validators (LC-1) | `services/model-service/src/services/nfl_eval_prep/asof.py` |
| L-1 / L-2 contracts + L-3 flags | `…/leaks.py` + `docs/research/NFL_EVAL_PREP_L1_L2_LEAK_FIX_DIFF.md` |
| Expanding-window splits, train-only | `…/splits.py` |
| Local input path (803ceb4e) | `…/local_path.py` |
| Local tree check (not a runner / not a gate) | `…/local_tree_check.py` + `scripts/nfl/eval_prep/local_tree_check.py` |
| W8 capture (isolated) | `…/nfl_w8_capture/` + `scripts/nfl/w8_capture/dry_run.py` |
| Harness plan (no execute) | `…/harness.py` |
| Synthetic fixtures | `…/synthetic.py` |
| Tests | `services/model-service/tests/test_nfl_eval_prep.py` |

Runner hard-refuses: `DATABASE_URL`, odds keys, seasons ≥ 2024, 2026 W4–W6, grading files under the feature tree. It does not call `simulate_nfl_game` and does not fit.

Production ingest/remat **unchanged** so this PR cannot rematerialize or drift W4–W6 plumbing.

---

## 5. Gap list (critical-path order)

Effort is **engineering scope**, not a calendar promise.

| # | Gap | Why it is on the critical path | Effort | Owner |
| - | --- | ------------------------------ | ------ | ----- |
| G0 | Ryan P-1 / P-2 / P-5 / P-6 rulings | Nothing gated may run; close source and CI unit are undecided | Decision only (no code) | Ryan |
| G1 | R-6 row list still missing → n=2998 unsupported | Cannot certify a 2998-game claim; must retract or re-earn | Small if off-repo file exists and can be hashed; **Large** if it must be rebuilt under LC-1 (and that rebuild is still not a cert) | Cursor / Alex |
| G2 | Apply L-1/L-2 on a **rebuild materializer** against a sealed 2013–2023 diagnostic lake (not 2024/2025) | Production still ships same-week + uncapped joins; prep only has the contract | Medium: new materializer job + as-of proof table writer; needs authorized local lake (R-2) | Cursor (after P-1 + data pin) |
| G3 | R-2 input manifest (source URL/tag/retrieval UTC/sha) for nflverse + owned lake | Rebuild is not reproducible without pins | Medium; **blocked on no-download / public-repo rules** until Ryan authorizes a private worktree | PR / Ryan |
| G4 | P-9 Railway recovery + `c57032db` v3 export | G2 feature-parity; IMV names it blocked on Railway | **UNKNOWN** from this repo (no Railway session). Not predictive. | Railway / PR / Ryan |
| G5 | P-3 key rotation + hist snapshot access | Only V-2-legal close source IMV will accept as primary | Ops + legal; not code in this PR | Ryan / PR |
| G6 | P-10 sealed pre-kickoff capture (2026 W8+) | Only clean G4 evidence | Medium service: weekly seal, tar sha, fail-closed if late | PR / Cursor |
| G7 | P-8 vs full 803ceb4e memo | This PR implements the **cited** rules; unseen clauses are UNKNOWN | Small once the memo is readable in a non-public worktree | Cursor |
| G8 | P-12 blind reimplementation + P-14 IMV metric script | LC-4 / LC-5: performer ≠ verifier | Medium (roles + second script). Not Cursor-solo. | CoS / Ryan / IMV |
| G9 | P-13 0444 pre-registration | Freeze splits/metrics/exclusions before any G3 diagnostic | Text; IMV N-1 | IMV / Ryan |
| G10 | P-4 results-source authorization + physically separate grading tree | LC-6 | Small once ruled | Ryan |
| G11 | Production L-1/L-2 remat change | Live board still leaky if used as “as-of” | Medium + **separate gate** (would remat; not this PR; do not mix with W4–W6) | Ryan must authorize |
| G12 | Totals / ML thresholds (PR-2 / PR-3) | Not certifiable | Decision | Ryan |
| G13 | V27–V62 safety stop | Out of scope; do not divert | n/a | — |

---

## 6. Track separation / what was not done

- No merge, no deploy, no production access, no external download.
- No `scripts/nfl/imv/` create or edit.
- No read/write of W4–W6 plumbing frozen inputs (`PRE_RETRO 20261022T173338Z`, v2.6.x bundles, runbooks, stores, seals).
- No evaluation on 2024, 2025, or 2026 W4–W6.
- No fabricated ATS/CLV/MAE.
- `c57032db` was not treated as predictive criteria.

**UNKNOWN** (explicit): off-repo location of a 2998 list; full text of IMV memos not in this public repo; Railway recovery ETA; whether SportsData ever fed game lines; exact 2024 week cut inside the 2992 train prefix.
