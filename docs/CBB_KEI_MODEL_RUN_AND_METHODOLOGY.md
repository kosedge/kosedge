# CBB KEI Model: Run Results & How the Model Gets There

**Purpose:** Enough detail to reproduce the run, audit the math, and get second opinions (e.g. other tools or reviewers) so we can work as a team.

**Run date:** 2026-02-21 (from `kei_backtest_results.json`).

---

## 1. What Was Run

- **Merge:** `python src/merge_games_ensemble.py`  
  - Reads: `full_ensemble_ratings.parquet`, `ncaab_historical_odds_open_close.parquet`, `actual_margins.parquet` (preferred over `results.csv`).  
  - Writes: `merged_games_with_odds_and_ratings.parquet`.
- **Backtest:** `python scripts/backtest_kei_results.py`  
  - Reads: `merged_games_with_odds_and_ratings.parquet`.  
  - Writes: `kei_backtest_results.json`.

No training step was re-run; the model uses **existing** `ensemble_weights.json` (see below).

---

## 2. Run Results (Summary)

| Metric | Value |
|--------|--------|
| **Total events in merged** | 10,270 (unique `event_id`) |
| **Events with actual_margin** | 406 |
| **Odds date range** | 2022-04-05 to 2025-12-06 |
| **Results date range** | 2022-11-07 to 2024-01-28 |

**Backtest (all 406 games with results; see “Bet rule” below):**

| Segment | n_games | wins | win_pct | total_units | roi_pct |
|---------|--------|------|---------|-------------|--------|
| Yesterday (2026-02-20) | 0 | 0 | — | 0 | — |
| This season (2026) | 0 | 0 | — | 0 | — |
| **All games (historical)** | **406** | **199** | **49.01%** | **-8.0** | **-1.97%** |

So over 406 games we **bet the model side every time**, flat 1 unit per game: **199 wins, 207 losses, -8 units, -1.97% ROI**.

**In-merge “edge only” summary (for context):**  
The merge script also prints a by-season backtest for games where **edge > 4 pts** (see “Edge rule” below). That subset is 361 games (249 in 2023, 112 in 2024); those numbers are **not** what’s in `kei_backtest_results.json`. The JSON backtest is **all 406** games, no edge filter.

---

## 3. Data Sources (Inputs)

- **Odds:** `data/processed/ncaab_historical_odds_open_close.parquet`  
  - The-odds-api historical NCAAB (open/close).  
  - Per event we use **consensus** close spread/total (mean across books).  
  - Columns used: `event_id`, `home_team`, `away_team`, `commence_time`, `close_spread_home`, `close_total` (then aggregated to `consensus_close_spread`, `consensus_close_total`).
- **Ratings:** `data/processed/full_ensemble_ratings.parquet`  
  - One row per `(year, team_norm)`.  
  - Columns: KenPom `adjem`, `adjoe`, `adjde`, `adjt`, `sos`; Torvik `net_torvik`, `barthag`; EvanMiya `bpr`; optional Haslam `haslam_net`.  
  - **As-of-date:** Merge uses KenPom (and Torvik) **weekly snapshots** when present (`kenpom_snapshots/`, `torvik_snapshots/`), joining by `game_date` with a backward-looking asof so we use ratings as of that date (no look-ahead).
- **Actual margins:** `data/processed/actual_margins.parquet`  
  - Rows: `(event_id, actual_margin)` (and optionally `actual_total`).  
  - Built by `build_actual_margins.py` from ESPN/Sports-Reference CSVs and/or SportsData.io parquets, matched to odds by `(game_date, home_team_norm, away_team_norm)`.
- **Ensemble weights:** `data/processed/ensemble_weights.json`  
  - Current contents (from a prior run of `estimate_ensemble_weights.py` on season ≤ 2022):  
    `{"adjem": 1, "torvik": 0, "barthag": 0, "bpr": 0, "haslam": 0, "home_court": 2.8696, "train_end_year": 2022, "n_train": 200}`  
  - So the **live** model is effectively **KenPom-only** (adjem diff + home court); other components have weight 0.

---

## 4. How the Model Gets There (Step by Step)

### 4.1 Team normalization and season

- Odds team names (e.g. `"Purdue Boilermakers"`) are shortened and normalized to `team_norm` (e.g. `"purdue"`) via `odds_team_to_short()`: take first word or first two words for 3+ word names, then lowercase, strip, and apply a small alias map (e.g. `unc` → `north carolina`).
- **Season** for a game: from `commence_time` date; if month ≥ 11, season = year + 1, else season = year (NCAAB convention).

### 4.2 Ratings join (no look-ahead)

- For each game we have `(home_team_norm, away_team_norm, game_date)`.
- We join **KenPom** (and Torvik) by `(team_norm, as_of_date)` with a **backward** asof on `game_date`, so we only use ratings known on or before the game date.
- Result: each game has `adjem`, `adjem_away`, `net_torvik`, `net_torvik_away`, `barthag`, `barthag_away`, `bpr`, `bpr_away`, and optionally `haslam_net`, `haslam_net_away`, plus `adjt`, `adjoe`, `adjde` and away variants when available.

### 4.3 Component diffs (clipped)

All diffs are **home minus away**, then clipped to **[-30, +30]** to avoid blowups from missing ratings:

- `adjem_diff = adjem - adjem_away` (KenPom adjusted efficiency margin)
- `torvik_diff = net_torvik - net_torvik_away`
- `barthag_diff = (barthag - barthag_away) * 20` (Barthag scaled)
- `bpr_diff = bpr - bpr_away` (EvanMiya BPR)
- `haslam_diff = haslam_net - haslam_net_away` (if present; else 0)

### 4.4 Ensemble spread formula

Weights from `ensemble_weights.json` (defaults if missing: adjem 0.40, torvik 0.30, barthag 0.15, bpr 0.10, haslam 0.05, home_court 3.75). **Current file** gives:

- `w_adjem = 1`, `w_torvik = w_barthag = w_bpr = w_haslam = 0`, `home_court = 2.8696`.

**Formula:**

```text
raw_spread = w_adjem * adjem_diff
          + w_torvik * torvik_diff
          + w_barthag * barthag_diff
          + w_bpr * bpr_diff
          + w_haslam * haslam_diff
          + home_court
ensemble_spread = clip(raw_spread, -28, 28)
```

So in the current run:

- **ensemble_spread = adjem_diff + 2.8696**, then clipped to [-28, 28].

Interpretation: **model predicted home margin** vs. the market’s **consensus close spread** (`consensus_close_spread`).

### 4.5 Edge rule (used in merge script and for “edge only” table)

- `spread_edge = ensemble_spread - consensus_close_spread`
- **edge_home:** `spread_edge > 4` (model likes home by more than 4 vs line)
- **edge_away:** `consensus_close_spread - ensemble_spread > 4` (model likes away by more than 4 vs line)

The **backtest in `kei_backtest_results.json` does NOT filter on edge**; it uses “bet model side” on all 406 games (see below).

### 4.6 Actual result and cover

- `actual_margin = home_pts - away_pts` (from actual_margins or results).
- **home_cover:** `actual_margin + consensus_close_spread > 0` (home beats the close spread).

### 4.7 Bet rule (what the backtest actually does)

For **every** game that has `actual_margin`:

- **Bet home** if `ensemble_spread > consensus_close_spread`, else **bet away**.
- One unit per game.  
  - If we bet home: **win 1 unit** if `home_cover`, else **lose 1 unit**.  
  - If we bet away: **win 1 unit** if not `home_cover`, else **lose 1 unit**.

So:

- `bet_home = (ensemble_spread > consensus_close_spread)`
- `bet_won = home_cover if bet_home else (1 - home_cover)` (boolean)
- `units = +1 if bet_won else -1`

**Wins** = number of games with `bet_won = true`. **Total units** = sum of `units`. **ROI%** = (total_units / n_games) × 100.

### 4.8 Optional: EV / logistic win prob (in merge only)

- `model_win_prob_home = 1 / (1 + exp(-k * spread_edge))` with `k = 0.15`.
- `implied_prob_home = 1 / (1 + exp(-k * consensus_close_spread))`.
- `ev_positive_home` / `ev_positive_away` compare model vs implied; these are **not** used in the backtest log.

---

## 5. Exact Numbers to Reproduce / Check

- **Merged parquet:** `apps/web/data/processed/merged_games_with_odds_and_ratings.parquet`
- **Backtest log:** `apps/web/data/processed/kei_backtest_results.json`
- **Ensemble weights:** `apps/web/data/processed/ensemble_weights.json`

To reproduce:

1. Dedupe merged by `event_id` (keep first).
2. Restrict to rows with non-null `actual_margin` (406 rows).
3. Add `game_date` from `commence_time` if needed; add `season` (Nov→year+1).
4. Line column: `consensus_close_spread`.
5. `home_cover = (actual_margin + consensus_close_spread) > 0`.
6. `bet_home = (ensemble_spread > consensus_close_spread)`.
7. `bet_won = home_cover if bet_home else !home_cover`.
8. `units = +1 if bet_won else -1`.
9. Sum wins and units over the 406 rows → **199 wins, -8 units, -1.97% ROI**.

---

## 6. Caveats for Second Opinions

- **Actual margins:** Many of the 406 come from SportsData.io **trial** data (scrambled). Good for pipeline and structure; not for claiming true performance.
- **Ensemble weights:** Trained on 200 games with season ≤ 2022; current weights are KenPom-only (adjem + home_court). Re-running `estimate_ensemble_weights.py` on more data would change weights and thus spread/edge/backtest.
- **Consensus close:** Single number per event (mean across books); no book-level backtest here.
- **No kelly or variable stake:** Flat 1u only.

---

## 7. Code References (for auditors)

- **Merge (spread, edge, actual, home_cover, units):** `apps/web/src/merge_games_ensemble.py` (esp. ~286–337 for diffs/weights, ~330–337 for edge, ~412–447 for actual and units).
- **Backtest (segment wins/units/ROI):** `apps/web/scripts/backtest_kei_results.py` (`_run_segment` and segment definitions).
- **Ensemble weight estimation:** `apps/web/src/estimate_ensemble_weights.py` (OLS on `actual_margin` vs component diffs + const; weights normalized to sum to 1, constant = home_court).

This document plus the three files above and the three data paths in §5 are enough to replicate the run and the backtest math for second opinions and team review.

---

## 8. What we can do next (ideas, no silver bullet)

The current backtest is “bet model side every game” → ~49% win rate, -1.97% ROI on 406 games. Below are concrete levers; none guarantee profit, but they’re the right places to push.

**Data (highest impact)**  
- **Real margins:** Replace SportsData trial (scrambled) with **ESPN-scraped results** for 2022–2025 so `actual_margin` is real. Then re-run merge + backtest.  
- **More seasons:** Add 2022 and 2025 results so we have multiple OOS years (and can do proper train/test by season).  
- **More games:** Extend odds + results so the backtest isn’t 400 games total.

**Ensemble (model itself)**  
- **Re-estimate weights:** Run `estimate_ensemble_weights.py` on **all** games with `actual_margin` (e.g. 406), or on a fixed train window (e.g. season ≤ 2023), then re-merge and backtest. Current weights were fit on 200 games (season ≤ 2022) and are KenPom-only.  
- **Try TRAIN_END_YEAR:** In `estimate_ensemble_weights.py`, try 2023 or 2024 as `TRAIN_END_YEAR` (if you have enough data) and compare OOS.  
- **Don’t zero out Torvik/Evan:** If the OLS gives small or negative weights, consider a floor (e.g. 10% each) instead of hard zero so the spread uses more signal.

**Simple filters (before any fancy EV)**  
- **Edge threshold:** Only count a “bet” when `|spread_edge| > 4` (or 5, 6) and backtest that subset. See if the model is right more often when it’s more confident.  
- **Complete ratings:** Only backtest games where both teams have non-null `adjem` (and optionally `net_torvik`) so we’re not betting on incomplete inputs.  
- **Conference / matchup:** Later, filter to conferences or game types where the model might be more stable (e.g. high-major only).

**Evaluation, not more complexity**  
- **By season:** Already in merge output; track ROI by season so we see if one year is dragging the total.  
- **CLV:** Compute (actual_margin + line) for the side we bet; average CLV > 0 would mean we’re beating the close on average even if ROI is negative (variance/juice).  
- **Hold off on EV/σ until the baseline beats the line:** If “bet every game” is -2% ROI, adding EV filters on top of the same spread often won’t fix it; better to improve the spread and data first, then reintroduce calibration/EV later.

**Totals**  
- We have `ensemble_total` and `total_edge` in the merge. Backtest totals (over/under) the same way we do spreads (model side vs consensus close) to see if there’s an edge there.

No single step is “the solution,” but: **better data + re-fit weights + simple filters + clear by-season and CLV checks** is a solid order of operations. Once the raw model (or a filtered slice) is at least break-even or positive CLV, we can layer on calibration and selective betting again.
